#!/usr/bin/env bash
# Crucible hook dispatcher — spawns adversary agents for verification.
# Called by hooks.json as: bash crucible-hooks.sh <phase1|phase2> <plugin_root>
set -euo pipefail

PHASE="${1:-}"
PLUGIN_ROOT="${2:-${CLAUDE_PLUGIN_ROOT:-.}}"
CRUCIBLE_DIR=".crucible"

mkdir -p "$CRUCIBLE_DIR"

phase1() {
    # Read the user's task from stdin (hook JSON payload)
    local input prompt
    input=$(cat)
    prompt=$(echo "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))" 2>/dev/null || echo "$input")

    if [ -z "$prompt" ]; then
        echo "Crucible: no prompt found in hook input" >&2
        exit 0
    fi

    echo "$prompt" > "$CRUCIBLE_DIR/task.md"
    echo "Crucible: task captured for adversarial verification"

    # Only spawn Phase 1 once per session
    if [ -f "$CRUCIBLE_DIR/verification-plan.md" ] || [ -f "$CRUCIBLE_DIR/.phase1-running" ]; then
        exit 0
    fi
    touch "$CRUCIBLE_DIR/.phase1-running"

    # Spawn Phase 1 adversary in background — plans verification before seeing code
    (
        claude -p \
            --system-prompt "You are the Crucible adversary agent (Phase 1 — Planning). Read $PLUGIN_ROOT/agents/adversary.md for your full system prompt and behavioral rules. Follow the PHASE 1 instructions exactly. Read .crucible/task.md for the user's original task. Build a verification plan BEFORE seeing any code changes. Write your plan to .crucible/verification-plan.md. Do NOT read any implementation files or diffs." \
            --allowedTools "Read" "Write" "Edit" "Bash(cat *)" "Bash(ls *)" "Bash(find *)" \
            --max-budget-usd 0.50 \
            --dangerously-skip-permissions \
            "Read $PLUGIN_ROOT/agents/adversary.md then read .crucible/task.md. Follow Phase 1 instructions: build a verification plan and write it to .crucible/verification-plan.md." \
            > /dev/null 2>&1
        rm -f "$CRUCIBLE_DIR/.phase1-running"
    ) &

    echo "Crucible: Phase 1 adversary spawned (planning verification)"
}

phase2() {
    # Only run Phase 2 once per stop event
    if [ -f "$CRUCIBLE_DIR/.phase2-running" ]; then
        exit 0
    fi
    touch "$CRUCIBLE_DIR/.phase2-running"

    # Capture the diff first
    bash "$PLUGIN_ROOT/scripts/parse-diff.sh"

    # Check if there's actually a diff to verify
    if [ ! -f "$CRUCIBLE_DIR/diff.md" ]; then
        rm -f "$CRUCIBLE_DIR/.phase2-running"
        echo "Crucible: no diff found, skipping verification"
        exit 0
    fi

    # Run Phase 2 adversary synchronously — asyncRewake handles the async part
    claude -p \
        --system-prompt "You are the Crucible adversary agent (Phase 2 — Execution). Read $PLUGIN_ROOT/agents/adversary.md for your full system prompt and behavioral rules. Follow the PHASE 2 instructions exactly. Read .crucible/verification-plan.md for your Phase 1 plan (if it exists). Read .crucible/diff.md for the code changes. Execute your verification plan against the actual changes. Run what was built. Classify findings by severity (Critical/Major/Minor). Write your report to .crucible/report.md. The last line of the report MUST be <!-- CRUCIBLE_VERDICT: PASS --> or <!-- CRUCIBLE_VERDICT: FAIL -->." \
        --allowedTools "Read" "Write" "Edit" "Bash" \
        --max-budget-usd 2.00 \
        --dangerously-skip-permissions \
        "Read $PLUGIN_ROOT/agents/adversary.md then read .crucible/diff.md and .crucible/verification-plan.md (if it exists). Follow Phase 2 instructions: execute verification, run what was built, write report to .crucible/report.md." \
        > /dev/null 2>&1

    rm -f "$CRUCIBLE_DIR/.phase2-running"

    # Check the verdict — exit 2 to trigger asyncRewake if findings exist
    if [ -f "$CRUCIBLE_DIR/report.md" ]; then
        if grep -q 'CRUCIBLE_VERDICT: FAIL' "$CRUCIBLE_DIR/report.md"; then
            echo "Crucible adversary found issues — see .crucible/report.md"
            cat "$CRUCIBLE_DIR/report.md"
            exit 2
        else
            echo "Crucible verification passed"
            exit 0
        fi
    else
        echo "Crucible: adversary did not produce a report"
        exit 0
    fi
}

case "$PHASE" in
    phase1) phase1 ;;
    phase2) phase2 ;;
    *)
        echo "Usage: crucible-hooks.sh <phase1|phase2> <plugin_root>" >&2
        exit 1
        ;;
esac
