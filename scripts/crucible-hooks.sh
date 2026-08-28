#!/usr/bin/env bash
# Crucible hook dispatcher — spawns adversary agents for verification.
# Called by hooks.json as: bash crucible-hooks.sh <phase1|phase2> <plugin_root>
set -euo pipefail

PHASE="${1:-}"
PLUGIN_ROOT="${2:-${CLAUDE_PLUGIN_ROOT:-.}}"
CRUCIBLE_DIR=".crucible"
MAX_ITERATIONS="${CRUCIBLE_MAX_ITERATIONS:-3}"
TRIGGER="${CRUCIBLE_TRIGGER:-@crucible}"

# Prevent recursive hook execution — Phase 1/2 claude -p subprocesses
# are themselves Claude Code sessions that would re-trigger these hooks
if [ "${CRUCIBLE_SUBPROCESS:-}" = "1" ]; then
    exit 0
fi

mkdir -p "$CRUCIBLE_DIR"

get_iteration() {
    if [ -f "$CRUCIBLE_DIR/iteration" ]; then
        cat "$CRUCIBLE_DIR/iteration"
    else
        echo "0"
    fi
}

phase1() {
    local input prompt
    input=$(cat)
    prompt=$(echo "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))" 2>/dev/null || echo "$input")

    if [ -z "$prompt" ]; then
        exit 0
    fi

    # Only activate if prompt contains the trigger keyword
    if ! echo "$prompt" | grep -qi "$TRIGGER"; then
        exit 0
    fi

    echo "$prompt" > "$CRUCIBLE_DIR/task.md"
    echo "Crucible: task captured for adversarial verification"

    # Only spawn Phase 1 once per session
    if [ -f "$CRUCIBLE_DIR/verification-plan.md" ] || [ -f "$CRUCIBLE_DIR/.phase1-running" ]; then
        exit 0
    fi
    touch "$CRUCIBLE_DIR/.phase1-running"

    (
        CRUCIBLE_SUBPROCESS=1 claude -p \
            --system-prompt "You are the Crucible adversary agent (Phase 1 — Planning). Read $PLUGIN_ROOT/agents/adversary.md for your full system prompt and behavioral rules. Follow the PHASE 1 instructions exactly. Read .crucible/task.md for the user's original task. Build a verification plan BEFORE seeing any code changes. Write your plan to .crucible/verification-plan.md. Do NOT read any implementation files or diffs." \
            --allowedTools "Read" "Write" "Edit" "Bash(cat *)" "Bash(ls *)" "Bash(find *)" \
            --max-budget-usd 0.50 \
            --dangerously-skip-permissions \
            "Read $PLUGIN_ROOT/agents/adversary.md then read .crucible/task.md. Follow Phase 1 instructions: build a verification plan and write it to .crucible/verification-plan.md." \
            > /dev/null 2>&1 || true
        rm -f "$CRUCIBLE_DIR/.phase1-running"
    ) </dev/null >/dev/null 2>&1 &
    disown $!

    echo "Crucible: Phase 1 adversary spawned (planning verification)"
}

phase2() {
    # Skip if Crucible wasn't activated for this session
    if [ ! -f "$CRUCIBLE_DIR/task.md" ]; then
        exit 0
    fi

    local iteration
    iteration=$(get_iteration)

    # Skip if already at max iterations
    if [ "$iteration" -ge "$MAX_ITERATIONS" ]; then
        exit 0
    fi

    # Skip if Phase 2 is already running
    if [ -f "$CRUCIBLE_DIR/.phase2-running" ]; then
        exit 0
    fi

    trap 'rm -f "$CRUCIBLE_DIR/.phase2-running"' EXIT
    touch "$CRUCIBLE_DIR/.phase2-running"

    # Move previous report out of the way for re-verification
    if [ -f "$CRUCIBLE_DIR/report.md" ]; then
        mv "$CRUCIBLE_DIR/report.md" "$CRUCIBLE_DIR/report-${iteration}.md"
    fi

    # Re-capture the diff each iteration
    bash "$PLUGIN_ROOT/scripts/parse-diff.sh" || true

    if [ ! -f "$CRUCIBLE_DIR/diff.md" ]; then
        echo "Crucible: no changes to verify" >&2
        exit 0
    fi

    # Increment iteration counter
    iteration=$((iteration + 1))
    echo "$iteration" > "$CRUCIBLE_DIR/iteration"

    CRUCIBLE_SUBPROCESS=1 claude -p \
        --system-prompt "You are the Crucible adversary agent (Phase 2 — Execution). Read $PLUGIN_ROOT/agents/adversary.md for your full system prompt and behavioral rules. Follow the PHASE 2 instructions exactly. Read .crucible/verification-plan.md for your Phase 1 plan (if it exists). Read .crucible/diff.md for the code changes. Execute your verification plan against the actual changes. Run what was built. Classify findings by severity (Critical/Major/Minor). Write your report to .crucible/report.md. The last line of the report MUST be <!-- CRUCIBLE_VERDICT: PASS --> or <!-- CRUCIBLE_VERDICT: FAIL -->." \
        --allowedTools "Read" "Write" "Edit" "Bash" \
        --max-budget-usd 2.00 \
        --dangerously-skip-permissions \
        "Read $PLUGIN_ROOT/agents/adversary.md then read .crucible/diff.md and .crucible/verification-plan.md (if it exists). Follow Phase 2 instructions: execute verification, run what was built, write report to .crucible/report.md." \
        > /dev/null 2>&1 || true

    if [ ! -f "$CRUCIBLE_DIR/report.md" ]; then
        echo "Crucible: adversary did not produce a report" >&2
        exit 2
    fi

    if grep -q 'CRUCIBLE_VERDICT: PASS' "$CRUCIBLE_DIR/report.md"; then
        # PASS — show findings but don't rewake for fixes
        {
            echo "Crucible: PASSED verification (iteration $iteration/$MAX_ITERATIONS)"
            echo ""
            cat "$CRUCIBLE_DIR/report.md"
        } >&2
        exit 2
    fi

    if [ "$iteration" -ge "$MAX_ITERATIONS" ]; then
        # Max iterations reached — show final report, stop looping
        {
            echo "Crucible: FAILED — max iterations reached ($iteration/$MAX_ITERATIONS)"
            echo "Crucible: review .crucible/report.md for remaining findings"
            echo ""
            cat "$CRUCIBLE_DIR/report.md"
        } >&2
        exit 2
    fi

    # FAIL with iterations remaining — rewake so Claude fixes the issues
    {
        echo "Crucible: FAILED verification (iteration $iteration/$MAX_ITERATIONS)"
        echo "Crucible: fix the findings below. Crucible will re-verify automatically."
        echo ""
        cat "$CRUCIBLE_DIR/report.md"
    } >&2
    exit 2
}

phase2_wait() {
    # Skip if Crucible wasn't activated for this session
    if [ ! -f "$CRUCIBLE_DIR/task.md" ]; then
        exit 0
    fi

    # Synchronous companion to asyncRewake phase2 — shows spinner while Phase 2 runs
    local waited=0
    while [ ! -f "$CRUCIBLE_DIR/report.md" ] && [ "$waited" -lt 290 ]; do
        sleep 2
        waited=$((waited + 2))
    done
}

case "$PHASE" in
    phase1) phase1 ;;
    phase2) phase2 ;;
    phase2-wait) phase2_wait ;;
    *)
        echo "Usage: crucible-hooks.sh <phase1|phase2|phase2-wait> <plugin_root>" >&2
        exit 1
        ;;
esac
