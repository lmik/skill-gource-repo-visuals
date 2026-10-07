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

## License

MIT
