#!/usr/bin/env bash
# Capture the user's task from the UserPromptSubmit hook input (stdin JSON).
set -euo pipefail

mkdir -p .crucible

input=$(cat)
prompt=$(echo "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))" 2>/dev/null || echo "$input")

if [ -n "$prompt" ]; then
    echo "$prompt" > .crucible/task.md
    echo "Crucible: task captured for adversarial verification"
else
    echo "Crucible: no prompt found in hook input" >&2
fi
