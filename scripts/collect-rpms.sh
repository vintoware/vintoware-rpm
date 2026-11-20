#!/usr/bin/env bash
# Download the RPMs to publish: the newest <keep> releases of every package.
# Release tags are `<name>/<evr>`; `gh release list` returns newest first.
#
#   collect-rpms.sh <dest-dir> [keep]
set -euo pipefail
dest=$1 keep=${2:-3}
mkdir -p "$dest"

declare -A seen=()
while read -r tag; do
  [[ "$tag" == */* ]] || continue
  name=${tag%%/*}
  count=${seen[$name]:-0}
  ((count < keep)) || continue
  seen[$name]=$((count + 1))
  echo "collecting $tag"
  gh release download "$tag" --pattern '*.rpm' --dir "$dest/${tag//\//_}" --clobber
done < <(gh release list --limit 500 --exclude-drafts --json tagName --jq '.[].tagName')
