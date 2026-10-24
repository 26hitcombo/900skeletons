#!/usr/bin/env bash
# Publishes recent images to a throwaway "images" branch.
# The branch is rebuilt from scratch and force-pushed on every run, so old
# images (and their history) never pile up in the repo.
set -euo pipefail
: "${REMOTE:?REMOTE must be set}"
KEEP_DAYS="${KEEP_DAYS:-7}"
OUT="$(pwd)/output"
WORK="$(mktemp -d)"

# Start from the images already on the branch (if it exists yet)
if git ls-remote --exit-code --heads "$REMOTE" images >/dev/null 2>&1; then
  git clone --quiet --depth 1 --branch images "$REMOTE" "$WORK"
  rm -rf "$WORK/.git"
fi

cp "$OUT"/*.jpg "$WORK"/

# Drop images older than KEEP_DAYS (judged by the date in the filename)
cutoff=$(date -u -d "$KEEP_DAYS days ago" +%F)
for f in "$WORK"/*.jpg; do
  [ -e "$f" ] || continue
  d=$(basename "$f" .jpg)
  if [[ "$d" < "$cutoff" ]]; then rm "$f"; fi
done

cd "$WORK"
git init --quiet -b images
git add -A
git -c user.name="daily-bot" -c user.email="daily-bot@users.noreply.github.com" \
    commit --quiet -m "Images up to $(date -u +%F)"
git push --quiet --force "$REMOTE" images
echo "Published $(ls -1 *.jpg | wc -l) image(s) to the images branch"
