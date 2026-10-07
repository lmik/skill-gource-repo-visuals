"""Current-version timeline: the highest semver tag reached so far (tags reachable from REF).

usage: versions.py REPO REF WORK   -> WORK/versions.json  [(commit_ts, tag), ...]
"""
import json, re, subprocess, sys

REPO, REF, WORK = sys.argv[1:4]
SEMVER = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:-(.+))?$")


def git(*a, check=True):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, check=check)


def key(tag):
    m = SEMVER.match(tag)
    if not m:
        return None
    ma, mi, pa, suf = m.groups()
    rank = 1 if suf is None else (2 if suf.lower().startswith("fix") else 0)  # -RCn before release, -fix.N after
    n = re.search(r"(\d+)$", suf or "")
    return int(ma), int(mi), int(pa), rank, int(n.group(1)) if n else 0


tags = []
for t in git("for-each-ref", "refs/tags", "--format=%(refname:strip=2)").stdout.split():
    ref = f"refs/tags/{t}"  # fully qualified: some tag names collide with branch names
    if key(t) and git("merge-base", "--is-ancestor", ref, REF, check=False).returncode == 0:
        tags.append((int(git("log", "-1", "--format=%ct", ref).stdout), t))

best, events, skipped = None, [], []
for ts, t in sorted(tags):
    if best is None or key(t) > best:
        best = key(t)
        events.append((ts, t))
    else:
        skipped.append(t)
json.dump(events, open(f"{WORK}/versions.json", "w"))
print(f"{len(events)} version changes, first {events[0][1]}, last {events[-1][1]}")
print("skipped (lower than the version already shown):", skipped)
