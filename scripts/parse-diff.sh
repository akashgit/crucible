#!/usr/bin/env bash
# Diff parser for Crucible adversary — captures what changed during a session
# and writes a structured summary for the adversary to consume.

set -euo pipefail

CRUCIBLE_DIR="${CRUCIBLE_DIR:-.crucible}"
MAX_CHARS=50000

mkdir -p "$CRUCIBLE_DIR"

diff_output=$(git diff HEAD 2>/dev/null || true)

if [ -z "$diff_output" ]; then
    diff_output=$(git diff --cached 2>/dev/null || true)
fi

if [ -z "$diff_output" ]; then
    diff_output=$(git diff HEAD~1 HEAD 2>/dev/null || true)
fi

if [ -z "$diff_output" ]; then
    echo "No changes detected."
    exit 0
fi

full_diff="$diff_output"

files_added=$(echo "$full_diff" | grep -c '^+++ b/' 2>/dev/null || echo "0")
files_summary=$(echo "$full_diff" | grep '^+++ b/' | sed 's|^+++ b/||' || true)

insertions=$(echo "$full_diff" | grep -c '^+[^+]' 2>/dev/null || echo "0")
deletions=$(echo "$full_diff" | grep -c '^-[^-]' 2>/dev/null || echo "0")

languages=""
while IFS= read -r file; do
    ext="${file##*.}"
    case "$ext" in
        py) languages="$languages Python" ;;
        js) languages="$languages JavaScript" ;;
        ts) languages="$languages TypeScript" ;;
        sh) languages="$languages Shell" ;;
        md) languages="$languages Markdown" ;;
        json) languages="$languages JSON" ;;
        go) languages="$languages Go" ;;
        rs) languages="$languages Rust" ;;
        rb) languages="$languages Ruby" ;;
        java) languages="$languages Java" ;;
        *) languages="$languages $ext" ;;
    esac
done <<< "$files_summary"

languages=$(echo "$languages" | tr ' ' '\n' | sort -u | tr '\n' ' ' | sed 's/^ //;s/ $//')

truncated_diff="$full_diff"
if [ "${#full_diff}" -gt "$MAX_CHARS" ]; then
    truncated_diff="${full_diff:0:$MAX_CHARS}

... [TRUNCATED — full diff is ${#full_diff} characters, showing first $MAX_CHARS]"
fi

cat > "$CRUCIBLE_DIR/diff.md" << DIFFEOF
# Changes Summary

- **Files changed:** $files_added
- **Lines added:** $insertions
- **Lines removed:** $deletions
- **Languages:** $languages

## Files

$files_summary

## Diff

\`\`\`diff
$truncated_diff
\`\`\`
DIFFEOF

echo "Diff written to $CRUCIBLE_DIR/diff.md ($files_added files, +$insertions/-$deletions lines)"
