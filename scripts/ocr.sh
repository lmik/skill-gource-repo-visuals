#!/bin/sh
# OCR the gource date strip of every frame.   usage: ocr.sh WORK   -> WORK/ocr.tsv  (frame<TAB>text)
if [ "$1" = "--one" ]; then
  # cd + bare filename: Leptonica rewrites paths that start with /tmp to $TMPDIR and then can't find them
  cd "$(dirname "$2")" || exit 1
  f=$(basename "$2")
  txt=$(tesseract "$f" - --psm 7 2>/dev/null | tr -d '\n')
  # --psm 7 (single line) returns nothing when a file label sits in the strip too; block mode copes
  if ! printf '%s' "$txt" | grep -qE '20[0-9]{2}.*[0-9]{2}:[0-9]{2}:[0-9]{2}'; then
    alt=$(tesseract "$f" - --psm 6 2>/dev/null | grep -E '20[0-9]{2}.*[0-9]{2}:[0-9]{2}:[0-9]{2}' | head -1)
    [ -n "$alt" ] && txt=$alt
  fi
  printf '%s\t%s\n' "$(basename "$f" .png)" "$txt"
  exit 0
fi
ls "$1"/date/*.png | xargs -P 10 -n 1 "$0" --one | sort > "$1/ocr.tsv"
wc -l < "$1/ocr.tsv"
