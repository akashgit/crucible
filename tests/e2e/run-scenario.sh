#!/usr/bin/env bash
# Run a Crucible e2e test scenario.
#
# Usage: ./run-scenario.sh <scenario-name>
# Example: ./run-scenario.sh math
#
# This script sets up a test environment, simulates a primary agent's work,
# then runs the Crucible adversary against the result.
#
# NOTE: Full adversarial verification requires a Claude Code session.
# This script validates that the infrastructure works (diff parsing,
# report structure, file layout) but does not spawn the adversary agent.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SCENARIO="${1:-}"

if [ -z "$SCENARIO" ]; then
    echo "Usage: $0 <scenario>"
    echo "Available scenarios:"
    ls "$SCRIPT_DIR"/scenario-*.md 2>/dev/null | sed 's/.*scenario-//;s/\.md//'
    exit 1
fi

SCENARIO_FILE="$SCRIPT_DIR/scenario-${SCENARIO}.md"
if [ ! -f "$SCENARIO_FILE" ]; then
    echo "Error: Scenario file not found: $SCENARIO_FILE"
    exit 1
fi

echo "=== Crucible E2E Test: $SCENARIO ==="
echo ""

WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT

echo "1. Setting up test environment in $WORK_DIR"
cd "$WORK_DIR"
git init -q
git commit --allow-empty -m "initial" -q

cp "$ROOT_DIR/scripts/parse-diff.sh" .
chmod +x parse-diff.sh
mkdir -p .crucible

echo "2. Verifying parse-diff.sh works"
echo "test content" > test-file.txt
git add test-file.txt
git commit -m "add test file" -q

echo "more content" >> test-file.txt
bash parse-diff.sh

if [ -f .crucible/diff.md ]; then
    echo "   PASS: diff.md created"
    if grep -q "test-file.txt" .crucible/diff.md; then
        echo "   PASS: diff.md contains changed file"
    else
        echo "   FAIL: diff.md missing file reference"
        exit 1
    fi
else
    echo "   FAIL: diff.md not created"
    exit 1
fi

echo "3. Verifying scenario file is well-formed"
if grep -q "## Task Given to Primary Agent" "$SCENARIO_FILE"; then
    echo "   PASS: Has task description"
else
    echo "   FAIL: Missing task description"
    exit 1
fi

if grep -q "## What the Adversary Should Do" "$SCENARIO_FILE"; then
    echo "   PASS: Has adversary instructions"
else
    echo "   FAIL: Missing adversary instructions"
    exit 1
fi

if grep -q "### Phase 1" "$SCENARIO_FILE"; then
    echo "   PASS: Has Phase 1 section"
else
    echo "   FAIL: Missing Phase 1 section"
    exit 1
fi

if grep -q "### Phase 2" "$SCENARIO_FILE"; then
    echo "   PASS: Has Phase 2 section"
else
    echo "   FAIL: Missing Phase 2 section"
    exit 1
fi

if grep -q "## How to Run" "$SCENARIO_FILE"; then
    echo "   PASS: Has run instructions"
else
    echo "   FAIL: Missing run instructions"
    exit 1
fi

echo "4. Verifying report format template"
cat > .crucible/report.md << 'REPORT'
# Crucible Verification Report

## Summary
- **Task:** Test scenario validation
- **Verdict:** PASS
- **Iterations:** 1
- **Findings:** 0 Critical, 0 Major, 0 Minor

## Critical Findings
None

## Major Findings
None

## Minor Findings
None

## Verification Tests Executed
| # | Test | Result | Notes |
|---|------|--------|-------|
| 1 | parse-diff.sh works | PASS | diff.md created with correct content |
| 2 | scenario file well-formed | PASS | all required sections present |

## Unplanned Observations
None
REPORT

if grep -q "Verdict" .crucible/report.md; then
    echo "   PASS: Report template is valid"
else
    echo "   FAIL: Report template invalid"
    exit 1
fi

echo ""
echo "=== $SCENARIO: ALL INFRASTRUCTURE CHECKS PASSED ==="
echo ""
echo "To run the full adversarial test, start a Claude Code session and:"
echo "  1. Give Claude the task from $SCENARIO_FILE"
echo "  2. After completion, run /crucible-verify"
echo "  3. Check .crucible/report.md for findings"
