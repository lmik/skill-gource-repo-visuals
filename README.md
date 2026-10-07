# skill-gource-repo-visuals

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that renders a [gource](https://gource.io) video of a git branch, with a live stats overlay, as a QuickTime-playable MP4.

## What it does

The overlay updates per commit, in sync with the animation:

```
Codezeilen: 65.017                                              Version: v30.0.0
795 Dateien in 263 Ordnern
Änderungen: +158.006 / −93.426
```

- **Codezeilen:** lines in code files (`ts tsx js jsx mjs cjs mts cts css scss sql prisma sh`); lockfiles, docs and assets aren't counted.
- **Dateien / Ordner:** the files and folders gource is currently showing.
- **Änderungen:** cumulative added and deleted code lines.
- **Version** (optional, `--show-version-tags`): the highest semver tag reached so far.

The final frame matches the real tree at the tip exactly. The numbers are anchored to every first-parent commit, so history-only (`-s ours`) merges and cherry-picked release copies aren't counted twice. Video time and commit time are matched by OCR-ing the date gource draws, because gource's auto-skip makes that mapping non-linear and it isn't the same from one render to the next.

## Installation

```bash
git clone <this repo> ~/Projects/skill-gource-repo-visuals
ln -s ~/Projects/skill-gource-repo-visuals ~/.claude/skills/gource-repo-visuals
```

## Usage

The skill only runs when you invoke it explicitly:

```
/gource-repo-visuals                       # stats overlay only
/gource-repo-visuals --show-version-tags   # plus the current version tag, top right
```

Claude asks for the repo, branch and output folder, then renders. A ~2-year history gives about 100 s of video and needs about 3 GB of scratch space.

## Requirements

gource, ffmpeg (with libx264), tesseract (with English data), git and Python ≥ 3.8. Pillow is installed into a scratch venv automatically. On a fresh machine the skill's first step runs `scripts/check-requirements.sh`, shows what's missing, and either installs it after your confirmation or walks you through it. To check by hand:

```bash
scripts/check-requirements.sh        # exit 0 = ready; otherwise prints the install commands
```

On macOS everything comes from Homebrew (`brew install gource ffmpeg tesseract`). Debian/Ubuntu works too (`apt-get install gource ffmpeg tesseract-ocr tesseract-ocr-eng python3-venv`, plus `xvfb` when there's no display). On Windows, use WSL.

## License

MIT
