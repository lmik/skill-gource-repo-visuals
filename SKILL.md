---
name: gource-repo-visuals
description: Render a gource video of a git branch with a stats overlay (code lines, files/folders, +/- lines; current version tag with --show-version-tags) as a QuickTime-playable MP4.
disable-model-invocation: true
---

# Gource video with stats overlay

Produces a 1920×1080 / 60 fps MP4 of a branch's history. The top left shows `Lines of code: …` / `… files in … folders` / `Changes: +… / −…`, and with `--show-version-tags` the top right shows `Version: vX.Y.Z`. All of it updates per commit, in sync with the animation. `--lang de` switches the labels and number formatting to German (`Codezeilen: 65.017` / `… Dateien in … Ordnern` / `Änderungen: …`).

Use 1920×1080 throughout: the date-strip crop in step 4 depends on that resolution.

## How it works

The final values have to be **exact**, so check them against the real tip, and **in sync** with the animation.

- **In sync:** gource's `--auto-skip-seconds` skips quiet periods, which makes video time a non-linear function of commit time. Gource can't tell you that mapping, so it's read back from the video: OCR the date gource draws at the top centre of every frame.
- **Exact:** summing per-commit numstat drifts by about 10%. History-only (`-s ours`) merges and merge-backs of cherry-picked release/prod copies throw away changes that a plain sum still counts. `timeline.py` anchors every value to the real tree of the latest first-parent commit. Not-yet-merged side commits sit on top as pending deltas, but only if their merge actually carries their change into `REF`.

## Steps

### 1. Inputs

Settle these, and set them once for every later step:

```sh
S=<this skill's base directory>/scripts
REPO=<absolute repo path>   REF=<branch>   WORK=<new empty dir>   OUT=<output dir>
VFLAG=--show-version-tags   # only if the invocation arguments contain it; otherwise VFLAG=
LFLAG="--lang de"           # only if the invocation arguments contain it; otherwise LFLAG=
```

- `REPO` defaults to the git repo of the current directory.
- `REF` defaults to the remote's default branch (`git -C "$REPO" symbolic-ref --short refs/remotes/origin/HEAD`, minus `origin/`).
- `WORK` defaults to a fresh `mktemp -d`.
- `OUT` defaults to `REPO`'s root, where the MP4 stays untracked.

Ask the user only for what neither the invocation nor these defaults settle.

The **version label** is opt-in. When `$VFLAG` is empty, skip `versions.py` and every version check; the repo needs no tags at all.

**Done when:** all five path/ref variables are set and `REPO` is a git repo that contains `REF`.

### 2. Requirements

```sh
$S/check-requirements.sh "$(dirname "$WORK")"
```

The script prints `ok` / `missing` / `warn` per item (Homebrew or apt, Xcode Command Line Tools, git, gource, ffmpeg with libx264, tesseract with English data, python3 ≥ 3.8 with venv, gource's font, swift, a display on Linux, free disk). It then prints one `INSTALL <what>: <command>` line per missing piece, and exits 0 only when nothing required is missing.

If the script reports anything `missing`, show the user the table and ask how to install it, with two options:

- **Automatic (recommended):** you run the `INSTALL` commands after this one confirmation. Commands that need a password or a GUI can't run from your shell: the Homebrew installer, `sudo apt-get` and `xcode-select --install`. Hand those to the user (run in their own terminal, or click through the Xcode dialog) and wait until they say they're done. Run `brew install …` yourself.
- **Guided:** for each missing item, in order (Xcode CLT → Homebrew → packages), give one line on what it's for, plus the exact command. The user runs it; you wait.

After Homebrew installs, it prints a `brew shellenv` line for the shell profile. If the check then says "installed but not on PATH", run that `eval` line in your own commands for the rest of the session and remind the user to add it to `~/.zprofile`.

Re-run the check after each round of installs. A `warn` doesn't block. Explain it once and continue:
- no swift: the playability check falls back to ffmpeg;
- headless Linux: prefix gource with `xvfb-run -a`;
- low disk: pick a `WORK` on a larger volume.

Then the Python dependency, which lives inside `WORK` and installs without asking:

```sh
python3 -m venv "$WORK/venv" && "$WORK/venv/bin/pip" install -q pillow
```

**Done when:** `check-requirements.sh` exits 0 and `"$WORK/venv/bin/python" -c 'import PIL'` succeeds.

### 3. Base video

Bring `REF` up to date without touching the user's checkout:

```sh
git -C "$REPO" fetch origin --tags
git -C "$REPO" merge-base --is-ancestor $REF origin/$REF
```

If `REF` is behind and isn't checked out, fast-forward it with `git -C "$REPO" fetch origin $REF:$REF`. If it is checked out, ask before pulling.

Gource visualises `HEAD`, and v0.56 has no branch option, so feed it a log of `REF`. Pipe its output straight into ffmpeg. An intermediate `.ppm` file would be about 6 MB per frame, roughly 30 GB for 100 s.

```sh
git -C "$REPO" log $REF --reverse --raw --encoding=UTF-8 --no-renames --no-show-signature \
  --pretty=format:user:%aN%n%ct > "$WORK/gource.log"
gource "$WORK/gource.log" --log-format git --hide usernames --seconds-per-day 0.1 --auto-skip-seconds 1 \
  -1920x1080 -o - | ffmpeg -y -r 60 -f image2pipe -vcodec ppm -i - -vcodec libx264 -preset ultrafast \
  -pix_fmt yuv420p -crf 1 -threads 0 -bf 0 "$WORK/base.avi"
```

- Gource opens a window while it renders. That window is the render, so it has to stay open.
- Leave gource's date display on: step 4 reads it.
- The AVI is only an intermediate, because QuickTime can't play AVI.
- Homebrew's ffmpeg has no `drawtext`/`subtitles` filters, so the overlay is drawn with Pillow later.

**Done when:** the local `REF` equals `origin/REF`, `ffprobe` reports 1920×1080 at 60/1 fps, and the duration is about (days of history × 0.1 s) minus skipped quiet periods.

### 4. Frame → time map

```sh
mkdir "$WORK/date"
ffmpeg -v error -i "$WORK/base.avi" -vf "crop=760:40:580:8,format=gray,negate,scale=1520:80" "$WORK/date/%05d.png"
$S/ocr.sh "$WORK"
python3 $S/frametimes.py "$WORK"
```

Gource's timing isn't deterministic: two renders of the same log came out at 6,053 and 6,125 frames. So the map belongs to this one render; always OCR the exact `base.avi` you composite onto.

File names drifting under the date garble between 1 frame in 100 and 1 in 6, depending on the render.

- `ocr.sh` falls back from tesseract `--psm 7` (single line), which returns nothing when a label shares the strip, to `--psm 6` (block mode).
- `frametimes.py` keeps the longest non-decreasing run of parsed timestamps as trusted anchors. It rebuilds frames whose day or month is garbled from year plus time of day between two anchors, and interpolates the rest.
- `ocr.sh` `cd`s into the folder before calling tesseract, because Leptonica rewrites paths starting with `/tmp` to `$TMPDIR` and then reports the file as missing.

**Done when:** the number of PNGs equals the number of frames, `ocr.tsv` has one line per frame, and `frametimes.py` reports more than 95% trusted with a max gap under one second (60 frames). If it doesn't, open a few failing crops and adjust the crop box before going on.

### 5. Stats and versions

```sh
python3 $S/timeline.py "$REPO" $REF "$WORK"
[ -n "$VFLAG" ] && python3 $S/versions.py "$REPO" $REF "$WORK"
```

- **Lines of code:** lines in code files only (the `CODE` set in `timeline.py`). Lockfiles, SVG, Markdown, JSON and YAML are left out.
- **Changes:** cumulative added and deleted code lines, with the same carry rule, so cherry-picked copies count once. Its net (added − deleted) ends a few hundred lines away from lines of code because conflict resolutions inside merges aren't counted.
- **Version** (version label only): the highest semver tag reached so far. Backported hotfix tags that arrive after a higher version (e.g. a prod `v28.0.x` after `v30.0.0`) never show, because otherwise the version would run backwards. `-RCn` sorts before its release and `-fix.N` after it. Tags that aren't semver are ignored.

**Done when:** the `final` line of `timeline.py` equals its `truth` line for loc, files and dirs. A mismatch means the replay logic is wrong; fix it rather than shipping. Also scan the biggest jumps between consecutive events: each one should match a real commit (a reformat, a big feature), not double counting that gets corrected at a later merge.

### 6. Preview

```sh
ffmpeg -v error -ss 50 -i "$WORK/base.avi" -frames:v 1 "$WORK/bg.png"
"$WORK/venv/bin/python" $S/overlay.py "$WORK" $VFLAG $LFLAG --preview 3000 "$WORK/bg.png" "$WORK/preview.png"
```

**Done when:** you've looked at `preview.png` and the overlay is legible. The left block and the version should share the 56 px side margin and the 48 px top margin, and, with the version label, the version should match the tag that was current at the date gource shows.

### 7. Composite

```sh
"$WORK/venv/bin/python" $S/overlay.py "$WORK" $VFLAG $LFLAG | ffmpeg -v error -y -i "$WORK/base.avi" \
  -f rawvideo -pix_fmt rgba -s 1920x170 -r 60 -i - \
  -filter_complex "[0:v][1:v]overlay=0:0:shortest=1,format=yuv420p" \
  -c:v libx264 -preset slow -crf 18 -profile:v high -movflags +faststart "$OUT/gource.overlay.mp4"
```

Gource stops at the last commit that changes files, then idles for about 15 s. `overlay.py` folds later merge-only commits into the first second of that tail, so the video still ends on the tip's numbers.

**Done when:**
- the frame count equals the base video's;
- the last frame shows the `truth` values from step 5 and (with the version label) the newest version from step 5;
- the file plays: `swift $S/playable.swift <file>` prints `playable: true` on macOS. Without swift, `ffmpeg -v error -i <file> -f null -` must print nothing.

### 8. Hand over

Open the file: `open -a "QuickTime Player" <file>` on macOS, `xdg-open <file>` on Linux. If an earlier render with the same name is still open, QuickTime keeps showing the old one. Ask the user to close that window first, because the terminal usually isn't allowed to send Apple events to QuickTime.

Tell the user where the MP4 is and what its size is. Point out what isn't counted in the line numbers and, with the version label, any tags that were skipped. Leave `$WORK` and the 2 GB base AVI in place until the user says to delete them.
