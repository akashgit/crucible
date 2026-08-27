# Test Scenario: Hard Math Question

## Task Given to Primary Agent

> Prove that for all positive integers n, the sum of the first n odd numbers equals n squared.
> That is, prove: 1 + 3 + 5 + ... + (2n-1) = n^2
>
> Provide both an inductive proof and a constructive (visual/geometric) argument.
> Then write a Python script that verifies the identity for n = 1 to 10000.

## What the Adversary Should Do

### Phase 1 (Planning)

The adversary should identify:
- **Correctness criteria:** The inductive proof must have a valid base case (n=1: 1 = 1^2) and a valid inductive step (assume sum of first k odd = k^2, show sum of first k+1 odd = (k+1)^2). The constructive argument should be geometrically sound.
- **Verification tests:**
  1. Check the base case manually
  2. Verify the inductive step is logically valid (not just hand-wavy)
  3. Run the Python verification script
  4. Test edge cases: n=0, n=1, n=very large
  5. Check that (2n-1) is actually the nth odd number
- **Likely failure modes:**
  - Inductive step assumes what it's trying to prove
  - Python script has an off-by-one error (common with range() and odd numbers)
  - Constructive argument is vague or not actually constructive

### Phase 2 (Execution)

The adversary should:
1. Read the proof and check each logical step
2. Run the Python script: `python3 verify_odds.py`
3. Modify the script to test edge cases: n=0, negative numbers
4. Independently compute a few values to cross-check: sum(1,3,5,7) should be 16 = 4^2
5. Check that the script actually computes `sum(range(1, 2*n, 2))` and compares to `n**2`

### Expected Findings

A well-done proof should PASS with 0 Critical, 0 Major findings.

Common issues that would be findings:
- **Major:** Python script uses `range(1, 2*n+1, 2)` instead of `range(1, 2*n, 2)` — incorrect range for odd numbers (would include 2n+1 which is the (n+1)th odd)
- **Major:** Inductive step doesn't explicitly show that 2(k+1)-1 = 2k+1 is the next odd number
- **Minor:** Proof doesn't handle n=0 edge case (debatable whether 0 is a positive integer)

## How to Run

```bash
# This scenario requires a Claude Code session. To test manually:
# 1. Start Claude Code in a test directory
# 2. Give it the task above
# 3. After it completes, run /crucible-verify
# 4. Check .crucible/report.md for findings

# To verify the math independently:
python3 -c "
for n in range(1, 101):
    s = sum(range(1, 2*n, 2))
    assert s == n**2, f'Failed at n={n}: {s} != {n**2}'
print('All 100 cases verified: sum of first n odds = n^2')
"
```
