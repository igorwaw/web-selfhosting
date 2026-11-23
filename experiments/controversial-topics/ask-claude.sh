#!/bin/bash
# ask-claude.sh - the same questions for Claude Code, each in a fresh session.
# Runs from an empty temp directory, so no project CLAUDE.md gets into the context.
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$here/results-2"
cd "$(mktemp -d)"
for lang in en fr ru hy tr he ar; do
  echo "$(date +%T) claude $lang" >&2
  out="$here/results-2/claude-$lang.txt"
  : > "$out"
  while IFS=$'\t' read -r n q; do
    printf '## %s. %s\n\n%s\n\n' "$n" "$q" "$(claude -p "$q" < /dev/null)" >> "$out"
  done < "$here/questions-$lang.txt"
done
