#!/usr/bin/env bash
# Diff parser for Crucible adversary — captures what changed during a session
# and writes a structured summary for the adversary to consume.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$SCRIPT_DIR")}"

CRUCIBLE_DIR="${CRUCIBLE_DIR:-.crucible}"
MAX_CHARS=50000

mkdir -p "$CRUCIBLE_DIR"

# Most common case: changes were just committed, so check committed diff first
diff_output=$(git diff HEAD~1 HEAD -- ':!.crucible' 2>/dev/null || true)

# Fall back to uncommitted changes (staged or unstaged)
if [ -z "$diff_output" ]; then
    diff_output=$(git diff HEAD -- ':!.crucible' 2>/dev/null || true)
fi

if [ -z "$diff_output" ]; then
    diff_output=$(git diff --cached -- ':!.crucible' 2>/dev/null || true)
fi

# Handle untracked files — git diff doesn't see them, so temporarily
# mark them as intent-to-add and capture the diff
if [ -z "$diff_output" ]; then
    untracked=$(git ls-files --others --exclude-standard -- ':!.crucible' 2>/dev/null || true)
    if [ -n "$untracked" ]; then
        echo "$untracked" | xargs -I{} git add -N {} 2>/dev/null || true
        diff_output=$(git diff -- ':!.crucible' 2>/dev/null || true)
        git reset 2>/dev/null || true
    fi
fi

if [ -z "$diff_output" ]; then
    echo "Crucible: no changes detected"
    exit 0
fi

full_diff="$diff_output"

files_added=$(echo "$full_diff" | grep -c '^+++ b/' 2>/dev/null || true)
files_summary=$(echo "$full_diff" | grep '^+++ b/' | sed 's|^+++ b/||' || true)

insertions=$(echo "$full_diff" | grep -c '^+[^+]' 2>/dev/null || true)
deletions=$(echo "$full_diff" | grep -c '^-[^-]' 2>/dev/null || true)

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

echo "Crucible: diff captured ($files_added files, +$insertions/-$deletions lines)"
