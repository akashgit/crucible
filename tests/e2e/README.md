# Crucible E2E Test Scenarios

Three test scenarios that validate the adversary works across different task types.

## Scenarios

### 1. Hard Math (scenario-math.md)

A combinatorial identity proof: prove that the sum of the first n odd numbers equals n^2. Tests the adversary's ability to verify mathematical reasoning, check proofs for logical validity, and run numerical verification scripts.

### 2. FeatureBench Programming (scenario-featurebench.md)

Build a REST API rate limiter with token bucket, per-client limiting, pagination, and proper HTTP semantics. Tests the adversary's ability to start a server, exercise endpoints, verify rate limiting behavior, and check edge cases.

### 3. Bug Fix Programming (scenario-programming.md)

Find and fix a bug in a merge sort implementation (wrong variable increment in the merge step). Tests the adversary's ability to verify a bug fix is correct, run the fixed code, and confirm all test cases pass including performance on 1M elements.

## Running Tests

### Infrastructure validation (no Claude Code needed)

```bash
# Run all scenarios through infrastructure checks
for scenario in math featurebench programming; do
    bash tests/e2e/run-scenario.sh "$scenario"
done
```

This validates:
- parse-diff.sh captures diffs correctly
- Scenario files have required sections
- Report template format is valid

### Full adversarial tests (requires Claude Code)

For each scenario:

1. Create a clean test directory
2. Start a Claude Code session: `claude`
3. Give Claude the task from the scenario file
4. After Claude completes the task, type `/crucible-verify`
5. Read `.crucible/report.md` for the adversary's findings
6. Compare findings against the "Expected Findings" section in the scenario

### What to check in the report

- **Verdict** is PASS or FAIL (appropriate for the scenario)
- **Findings** include evidence (command + output) for every issue found
- **Iteration count** shows the adversary looped if needed (max 3)
- **All severity levels** are correctly classified
- The adversary **actually ran** what was built (not just read the code)
