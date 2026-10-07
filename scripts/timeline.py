"""Per-commit stats (code lines, files, dirs, cumulative +/-) in gource order, anchored to dev's real trees.

usage: timeline.py REPO REF WORK   -> WORK/timeline.json
"""
import json, subprocess, sys

REPO, REF, WORK = sys.argv[1:4]
CODE = {"ts", "tsx", "js", "jsx", "mjs", "cjs", "mts", "cts", "css", "scss", "sql", "prisma", "sh"}


def is_code(p):
    b = p.rsplit("/", 1)[-1]
    return "." in b and b.rsplit(".", 1)[-1].lower() in CODE


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, check=True).stdout


def dirs_of(paths):
    d = set()
    for p in paths:
        parts = p.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            d.add("/".join(parts[:i]))
    return d


# Events in the exact order gource replays them (same `git log` ordering as `gource --log-command git`).
events, cur = [], None
log = git("log", REF, "--reverse", "--raw", "--numstat", "--no-renames", "--encoding=UTF-8", "--no-show-signature",
          "--format=@@%H %ct")
for line in log.splitlines():
    if line.startswith("@@"):
        if cur:
            events.append(cur)
        h, ts = line[2:].split(" ")
        cur = {"h": h, "ts": int(ts), "raw": [], "loc": 0, "add": 0, "del": 0}
    elif line.startswith(":"):
        meta, path = line.split("\t", 1)
        cur["raw"].append((meta.split()[-1][0], path))
    elif line:
        a, d, path = line.split("\t", 2)
        if a != "-" and is_code(path):
            cur["loc"] += int(a) - int(d)
            cur["add"] += int(a)
            cur["del"] += int(d)
events.append(cur)

# True tree of every first-parent commit, and which commits each one absorbs.
fp = git("rev-list", "--first-parent", "--reverse", REF).split()
empty = git("hash-object", "-t", "tree", "/dev/null").strip()
truth, absorbed_at, absorbs = {}, {}, {}
files, loc, prev = set(), 0, empty
for c in fp:
    for line in git("diff", "--numstat", "--no-renames", prev, c).splitlines():
        a, d, p = line.split("\t", 2)
        if a != "-" and is_code(p):
            loc += int(a) - int(d)
    for line in git("diff", "--name-status", "--no-renames", prev, c).splitlines():
        st, p = line.split("\t", 1)
        if st[0] == "D":
            files.discard(p)
        else:
            files.add(p)
    truth[c] = (frozenset(files), loc)
    rng = git("rev-list", c if prev == empty else f"{prev}..{c}").split()
    for h in rng:
        absorbed_at[h] = c
    absorbs[c] = [h for h in rng if h != c]
    prev = c
fpset = set(fp)

# A merge only "carries" its side commits if it really brings their change into REF. History-only
# (-s ours) merges and merge-backs of cherry-picked release/prod copies would otherwise double count.
ev_by_h = {e["h"]: e for e in events}
carries = {}
for i, c in enumerate(fp[1:], 1):
    if not absorbs[c]:
        continue
    p = fp[i - 1]
    delta = truth[c][1] - truth[p][1]
    side = sum(ev_by_h[h]["loc"] for h in absorbs[c] if h in ev_by_h)
    same_tree = truth[c][0] == truth[p][0] and delta == 0
    carries[c] = not same_tree and (side == 0 or 0.5 <= delta / side <= 1.5)

# Replay: shown state = true tree of the latest first-parent commit + not-yet-merged side commits.
base_files, base_loc = frozenset(), 0
pending = {}
out, eff, adds, dels = [], 0, 0, 0
for e in events:
    h = e["h"]
    eff = max(eff, e["ts"])  # gource processes the queue in order, so time never runs backwards
    counted = h in fpset or carries.get(absorbed_at.get(h))
    if h in fpset:
        base_files, base_loc = truth[h]
        pending = {k: v for k, v in pending.items() if absorbed_at.get(k) != h}
    elif counted:
        pending[h] = e
    fs = set(base_files)
    for pe in pending.values():
        for st, p in pe["raw"]:
            if st == "D":
                fs.discard(p)
            else:
                fs.add(p)
    if counted:
        adds += e["add"]
        dels += e["del"]
    out.append({"h": h, "eff": eff, "loc": base_loc + sum(p["loc"] for p in pending.values()),
                "files": len(fs), "dirs": len(dirs_of(fs)), "add": adds, "del": dels})
json.dump(out, open(f"{WORK}/timeline.json", "w"))

tip_files, tip_loc = truth[fp[-1]]
last = out[-1]
print(f"events {len(out)}, non-carrying merges {sum(1 for v in carries.values() if not v)}/{len(carries)}")
print(f"final  loc {last['loc']} files {last['files']} dirs {last['dirs']} +{last['add']} -{last['del']}")
print(f"truth  loc {tip_loc} files {len(tip_files)} dirs {len(dirs_of(tip_files))}")
