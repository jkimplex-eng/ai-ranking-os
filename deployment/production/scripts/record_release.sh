#!/bin/sh
set -eu

: "${1:?Usage: record_release.sh ENV_FILE BUILD_SHA IMAGE_TAG}"
: "${2:?Usage: record_release.sh ENV_FILE BUILD_SHA IMAGE_TAG}"
: "${3:?Usage: record_release.sh ENV_FILE BUILD_SHA IMAGE_TAG}"
env_file=$1
build_sha=$2
image_tag=$3

case "$build_sha$image_tag" in
  *[!a-fA-F0-9]*)
    echo "Release identifiers must be hexadecimal git revisions" >&2
    exit 2
    ;;
esac
test -f "$env_file"

umask 077
temporary=$(mktemp "${env_file}.release.XXXXXX")
trap 'rm -f "$temporary"' EXIT HUP INT TERM
awk -v sha="$build_sha" -v tag="$image_tag" '
  /^BUILD_SHA=/ { print "BUILD_SHA=" sha; seen_sha=1; next }
  /^IMAGE_TAG=/ { print "IMAGE_TAG=" tag; seen_tag=1; next }
  { print }
  END {
    if (!seen_sha) print "BUILD_SHA=" sha
    if (!seen_tag) print "IMAGE_TAG=" tag
  }
' "$env_file" > "$temporary"
chmod --reference="$env_file" "$temporary"
mv -f "$temporary" "$env_file"
trap - EXIT HUP INT TERM
