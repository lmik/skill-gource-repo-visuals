#!/bin/sh
# Check everything the skill needs.  usage: check-requirements.sh [SCRATCH_DIR]
# One line per item: "ok|missing|warn  <item>  <detail>", then the install commands for whatever is missing.
# Exit 0 when every required item is present (warnings allowed), 1 otherwise.

SCRATCH=${1:-${TMPDIR:-/tmp}}
OS=$(uname -s)
missing=0
BREW_PKGS=""
APT_PKGS=""

report() { printf '%-8s %-12s %s\n' "$1" "$2" "$3"; }
need() {  # need <item> <detail> <brew pkg> <apt pkg>
  report missing "$1" "$2"
  missing=1
  [ -n "$3" ] && BREW_PKGS="$BREW_PKGS $3"
  [ -n "$4" ] && APT_PKGS="$APT_PKGS $4"
}
have() { command -v "$1" >/dev/null 2>&1; }

# --- platform & package manager
if [ "$OS" = Darwin ]; then
  if have brew; then report ok homebrew "$(brew --prefix)"
  elif [ -x /opt/homebrew/bin/brew ] || [ -x /usr/local/bin/brew ]; then
    report missing homebrew "installed but not on PATH: eval \"\$($( [ -x /opt/homebrew/bin/brew ] && echo /opt/homebrew || echo /usr/local )/bin/brew shellenv)\""; missing=1
  else report missing homebrew "needed to install the tools below (https://brew.sh)"; missing=1; fi
  have xcrun && xcode-select -p >/dev/null 2>&1 && report ok xcode-clt "$(xcode-select -p)" \
    || { report missing xcode-clt "Command Line Tools provide git, python3 and swift: xcode-select --install"; missing=1; }
elif [ "$OS" = Linux ]; then
  have apt-get && report ok apt "Debian/Ubuntu package manager" || report warn apt "not Debian/Ubuntu: install the packages below with your package manager"
else
  report warn platform "$OS is untested (on Windows use WSL)"
fi

# --- tools
have git && report ok git "$(git --version | cut -d' ' -f3)" || need git "" "git" "git"

if have gource; then report ok gource "$(gource --help 2>&1 | head -1 | cut -d' ' -f2)"; else need gource "renders the animation" gource gource; fi

if have ffmpeg && have ffprobe; then
  if ffmpeg -hide_banner -encoders 2>/dev/null | grep -q libx264; then report ok ffmpeg "$(ffmpeg -version | head -1 | cut -d' ' -f3)"
  else need ffmpeg "installed without the libx264 encoder" ffmpeg ffmpeg; fi
else need ffmpeg "encodes and composites the video" ffmpeg ffmpeg; fi

if have tesseract; then
  if tesseract --list-langs 2>/dev/null | grep -qx eng; then report ok tesseract "$(tesseract --version 2>&1 | head -1 | cut -d' ' -f2)"
  else need tesseract "English language data (eng) missing" tesseract tesseract-ocr-eng; fi
else need tesseract "reads the date gource draws on each frame" tesseract "tesseract-ocr tesseract-ocr-eng"; fi

if have python3 && python3 -c 'import sys; sys.exit(sys.version_info < (3, 8))' 2>/dev/null; then
  if python3 -c 'import venv, ensurepip' 2>/dev/null; then report ok python3 "$(python3 -V | cut -d' ' -f2)"
  else need python3-venv "python3 can't create virtual environments" "" python3-venv; fi
else need python3 "3.8 or newer" python3 "python3 python3-venv"; fi

# --- gource's font (the overlay uses it to match gource's own text)
FONT=""
for f in "$GOURCE_FONT" "$(have brew && brew --prefix 2>/dev/null)/share/gource/fonts/FreeSans.ttf" \
         /usr/share/gource/fonts/FreeSans.ttf /usr/local/share/gource/fonts/FreeSans.ttf \
         /usr/share/fonts/truetype/freefont/FreeSans.ttf; do
  [ -n "$f" ] && [ -f "$f" ] && { FONT=$f; break; }
done
[ -n "$FONT" ] && report ok font "$FONT" || report warn font "FreeSans.ttf not found (comes with gource); set GOURCE_FONT=<any .ttf>"

# --- optional extras
if [ "$OS" = Darwin ]; then
  have swift && report ok swift "for the QuickTime playability check" || report warn swift "no QuickTime check; ffmpeg decode check is used instead"
fi
if [ "$OS" = Linux ] && [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; then
  have xvfb-run && report ok xvfb-run "headless: run gource via 'xvfb-run -a gource ...'" \
    || { need xvfb "gource needs a display; no \$DISPLAY set" "" xvfb; }
fi

# --- disk space (base AVI ~2 GB per 100 s of video, plus ~1 GB of OCR crops and the MP4)
free_kb=$(df -Pk "$SCRATCH" 2>/dev/null | awk 'NR==2 {print $4}')
if [ -n "$free_kb" ]; then
  free_gb=$((free_kb / 1024 / 1024))
  [ "$free_gb" -ge 5 ] && report ok disk "${free_gb} GB free in $SCRATCH" || report warn disk "only ${free_gb} GB free in $SCRATCH; plan ~3 GB per 100 s of video"
fi

# --- install commands for what's missing
if [ "$missing" = 1 ]; then
  echo
  [ "$OS" = Darwin ] && ! have brew && echo 'INSTALL homebrew: /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  [ "$OS" = Darwin ] && ! xcode-select -p >/dev/null 2>&1 && echo 'INSTALL xcode-clt: xcode-select --install'
  [ -n "$BREW_PKGS" ] && [ "$OS" = Darwin ] && echo "INSTALL brew: brew install$BREW_PKGS"
  [ -n "$APT_PKGS" ] && [ "$OS" = Linux ] && echo "INSTALL apt: sudo apt-get update && sudo apt-get install -y$APT_PKGS"
fi
exit $missing
