"""OCR'd gource date per frame -> epoch seconds; robust to garbage via LNDS + interpolation.

usage: frametimes.py WORK   -> WORK/frame-ts.json
"""
import bisect, json, re, sys, time
WORK = sys.argv[1]
MONTHS = "January February March April May June July August September October November December".split()
pat = re.compile(r"(\d{1,2})\s+(" + "|".join(MONTHS) + r")\W+(20\d\d)\s+(\d\d):(\d\d):(\d\d)")
rows = [l.rstrip("\n").split("\t") for l in open(f"{WORK}/ocr.tsv")]
raw = []
for _, txt in rows:
    m = pat.search(txt)
    if m:
        d, mo, y, H, M, S = m.groups()
        try: raw.append(time.mktime((int(y), MONTHS.index(mo) + 1, int(d), int(H), int(M), int(S), 0, 0, -1)))
        except Exception: raw.append(None)
    else: raw.append(None)
def trusted(vals):
    """Indices of the longest non-decreasing subsequence of parsed values."""
    idx = [i for i, v in enumerate(vals) if v is not None]
    tails, tails_i, prev = [], [], {}
    for i in idx:
        k = bisect.bisect_right(tails, vals[i])
        prev[i] = tails_i[k - 1] if k else None
        if k == len(tails): tails.append(vals[i]); tails_i.append(i)
        else: tails[k] = vals[i]; tails_i[k] = i
    keep, i = [], tails_i[-1] if tails_i else None
    while i is not None: keep.append(i); i = prev[i]
    return sorted(keep)


anchors = trusted(raw)
# Rescue: when day/month are garbled, year + time of day usually survive. Between two trusted
# neighbours, take the candidate date with that exact local time closest to the linear estimate.
tod = re.compile(r"(20\d\d)\D{0,3}(\d\d):(\d\d):(\d\d)")
rescued = 0
for a, b in zip(anchors, anchors[1:]):
    for j in range(a + 1, b):
        m = tod.search(rows[j][1]) if raw[j] is None else None
        if not m: continue
        H, M, Sec = int(m.group(2)), int(m.group(3)), int(m.group(4))
        est = raw[a] + (raw[b] - raw[a]) * (j - a) / (b - a)
        day = time.localtime(raw[a] - 86400)
        cands = []
        for k in range((int(raw[b] - raw[a]) // 86400) + 3):
            t = time.mktime((day.tm_year, day.tm_mon, day.tm_mday + k, H, M, Sec, 0, 0, -1))
            if raw[a] <= t <= raw[b] and time.localtime(t).tm_year == int(m.group(1)): cands.append(t)
        if cands:
            raw[j] = min(cands, key=lambda t: abs(t - est)); rescued += 1
anchors = trusted(raw)
out = [None] * len(raw)
for a in anchors: out[a] = raw[a]
for a, b in zip(anchors, anchors[1:]):
    for j in range(a + 1, b):
        out[j] = raw[a] + (raw[b] - raw[a]) * (j - a) / (b - a)
for j in range(anchors[0]): out[j] = raw[anchors[0]]
for j in range(anchors[-1] + 1, len(raw)): out[j] = raw[anchors[-1]]
gaps = [b - a - 1 for a, b in zip(anchors, anchors[1:]) if b - a > 1]
print(f"rescued {rescued}, trusted {len(anchors)}, interpolated {len(raw)-len(anchors)}, max gap {max(gaps)} frames")
json.dump(out, open(f"{WORK}/frame-ts.json", "w"))
tail = sum(1 for v in out if v == out[-1])
print("trailing frames at final time:", tail)
