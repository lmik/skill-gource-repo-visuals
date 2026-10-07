# skill-gource-repo-visuals

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that renders a [gource](https://gource.io) video of a git branch, with a live stats overlay, as a QuickTime-playable MP4.

## What it does

The overlay updates per commit, in sync with the animation:

```
Lines of code: 48,210                                            Version: v2.4.0
612 files in 187 folders
Changes: +121,530 / −73,320
```

- **Lines of code:** lines in source files of common languages (the `CODE` extension set in `scripts/timeline.py`; add your own there). Lockfiles, docs, data files and assets aren't counted.
- **Files / folders:** the files and folders gource is currently showing.
- **Changes:** cumulative added and deleted code lines.
- **Version** (optional, `--show-version-tags`): the highest semver tag reached so far.

Labels are English by default; `--lang de` switches them and the number formatting to German.

The final frame matches the real tree at the tip exactly. The numbers are anchored to every first-parent commit, so history-only (`-s ours`) merges and cherry-picked release copies aren't counted twice. Video time and commit time are matched by OCR-ing the date gource draws, because gource's auto-skip makes that mapping non-linear and it isn't the same from one render to the next.

## Installation

Clone the repo anywhere and make it visible to Claude Code as a skill named `gource-repo-visuals`, either for yourself or for a single project:

```bash
git clone <this repo> <clone dir>
ln -s "$(cd <clone dir> && pwd)" ~/.claude/skills/gource-repo-visuals                 # all your projects
ln -s "$(cd <clone dir> && pwd)" <some project>/.claude/skills/gource-repo-visuals     # just that project
```

Copying the folder instead of symlinking works too; a symlink just picks up `git pull` updates.

## Usage

The skill only runs when you invoke it explicitly:

```
/gource-repo-visuals                       # stats overlay only
/gource-repo-visuals --show-version-tags   # plus the current version tag, top right
/gource-repo-visuals --lang de             # German labels
```

By default it renders the current directory's repo, its remote's default branch, and writes `gource.overlay.mp4` to the repo root; Claude only asks about what it can't work out. A ~2-year history gives about 100 s of video and needs about 3 GB of scratch space.

## Requirements

gource, ffmpeg (with libx264), tesseract (with English data), git and Python ≥ 3.8. Pillow is installed into a scratch venv automatically. On a fresh machine the skill's first step runs `scripts/check-requirements.sh`, shows what's missing, and either installs it after your confirmation or walks you through it. To check by hand:

```bash
scripts/check-requirements.sh        # exit 0 = ready; otherwise prints the install commands
```

On macOS everything comes from Homebrew (`brew install gource ffmpeg tesseract`). Debian/Ubuntu works too (`apt-get install gource ffmpeg tesseract-ocr tesseract-ocr-eng python3-venv`, plus `xvfb` when there's no display). On Windows, use WSL.

## License

MIT
