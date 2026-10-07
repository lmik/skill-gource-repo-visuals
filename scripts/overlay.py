"""Raw RGBA overlay frames (stats top-left, version top-right), one per video frame, to stdout.

usage: overlay.py WORK [--show-version-tags] [--preview N BG.png OUT]
       without --preview: 1920x170 rgba frames on stdout; with it: frame N's panel composited onto BG.png
needs: Pillow; WORK/timeline.json, WORK/frame-ts.json (+ WORK/versions.json with --show-version-tags)
"""
import argparse, bisect, json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("work")
ap.add_argument("--show-version-tags", action="store_true")
ap.add_argument("--preview", nargs=3, metavar=("FRAME", "BG", "OUT"))
args = ap.parse_args()
WORK = args.work
W, H, FPS = 1920, 170, 60
FONT_SIZE = 24


def find_font():
    """gource's own FreeSans, so the overlay matches gource's text; GOURCE_FONT overrides."""
    try:
        brew = subprocess.run(["brew", "--prefix"], capture_output=True, text=True).stdout.strip()
    except OSError:
        brew = ""
    for f in (os.environ.get("GOURCE_FONT"), brew and f"{brew}/share/gource/fonts/FreeSans.ttf",
              "/usr/share/gource/fonts/FreeSans.ttf", "/usr/local/share/gource/fonts/FreeSans.ttf",
              "/usr/share/fonts/truetype/freefont/FreeSans.ttf"):
        if f and os.path.isfile(f):
            return ImageFont.truetype(f, FONT_SIZE)
    print("FreeSans.ttf not found, using Pillow's default font (set GOURCE_FONT)", file=sys.stderr)
    return ImageFont.load_default(size=FONT_SIZE)


FONT = find_font()
WHITE, GREEN, RED = (255, 255, 255), (87, 200, 110), (240, 90, 85)
LEFT, TOP, LINE, RIGHT = 56, 48, 34, 56

tl = json.load(open(f"{WORK}/timeline.json"))
ft = json.load(open(f"{WORK}/frame-ts.json"))
versions = json.load(open(f"{WORK}/versions.json")) if args.show_version_tags else []
eff = [e["eff"] for e in tl]
ver_ts = [v[0] for v in versions]
n = len(ft)

# gource stops at the last file-changing commit and idles ~15 s; merge-only commits after that
# (often the newest PR merges) are folded into the first second of the idle tail.
state_idx = [bisect.bisect_right(eff, t) - 1 for t in ft]
first_tail = next(i for i in range(n) if ft[i] == ft[-1])
rest = len(tl) - 1 - state_idx[first_tail]
for k in range(min(FPS, n - first_tail)):
    state_idx[first_tail + k] = state_idx[first_tail] + round(rest * (k + 1) / FPS)
for i in range(first_tail + FPS, n):
    state_idx[i] = len(tl) - 1
ZERO = {"loc": 0, "files": 0, "dirs": 0, "add": 0, "del": 0}


def version_at(i):
    t = ft[i] if i < first_tail else max(ft[i], eff[-1])
    j = bisect.bisect_right(ver_ts, t) - 1
    return versions[j][1] if j >= 0 else None


def de(x):
    return f"{x:,}".replace(",", ".")


cache = {}


def render(e, ver):
    key = (e["loc"], e["files"], e["dirs"], e["add"], e["del"], ver)
    if key in cache:
        return cache[key]
    cache.clear()  # full-width frames are 1.3 MB; states only move forward
    lines = [[(f"Codezeilen: {de(e['loc'])}", WHITE)],
             [(f"{de(e['files'])} Dateien in {de(e['dirs'])} Ordnern", WHITE)],
             [("Änderungen: ", WHITE), (f"+{de(e['add'])}", GREEN), (" / ", WHITE), (f"−{de(e['del'])}", RED)]]
    if ver:
        s = f"Version: {ver}"
        lines.append([(s, WHITE, W - RIGHT - FONT.getlength(s), TOP)])
    txt, shadow = Image.new("RGBA", (W, H)), Image.new("RGBA", (W, H))
    dt, ds = ImageDraw.Draw(txt), ImageDraw.Draw(shadow)
    for i, segs in enumerate(lines):
        x, y = LEFT, TOP + i * LINE
        for seg in segs:
            s, col = seg[:2]
            if len(seg) == 4:
                x, y = seg[2:]
            ds.text((x + 2, y + 2), s, font=FONT, fill=(0, 0, 0, 230))
            dt.text((x, y), s, font=FONT, fill=col + (255,))
            x += FONT.getlength(s)
    cache[key] = Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(2)), txt).tobytes()
    return cache[key]


def panel(i):
    return render(tl[state_idx[i]] if state_idx[i] >= 0 else ZERO, version_at(i))


if args.preview:
    i, bg_path, out_path = int(args.preview[0]), args.preview[1], args.preview[2]
    bg = Image.open(bg_path).convert("RGBA")
    bg.alpha_composite(Image.frombytes("RGBA", (W, H), panel(i)))
    bg.save(out_path)
else:
    out = sys.stdout.buffer
    for i in range(n):
        out.write(panel(i))
    print(f"frames {n}", file=sys.stderr)
