# Test Scenario: General Programming Question (Bug Fix)

## Task Given to Primary Agent

> The following merge sort implementation has a bug. Find and fix it.
> After fixing, the sort must handle: empty lists, single elements,
> duplicates, negative numbers, and lists up to 1 million elements.
>
> ```python
> def merge_sort(arr):
>     if len(arr) <= 1:
>         return arr
>     mid = len(arr) // 2
>     left = merge_sort(arr[:mid])
>     right = merge_sort(arr[mid:])
>     return merge(left, right)
>
> def merge(left, right):
>     result = []
>     i = j = 0
>     while i < len(left) and j < len(right):
>         if left[i] <= right[j]:
>             result.append(left[i])
>             i += 1
>         else:
>             result.append(right[j])
>             i += 1  # BUG: should increment j, not i
>     result.extend(left[i:])
>     result.extend(right[j:])
>     return result
> ```
>
> Write the fixed version and a test suite that covers all the required cases.

## What the Adversary Should Do

### Phase 1 (Planning)

The adversary should identify:
- **Correctness criteria:**
  - The bug is on the line `i += 1` in the else branch — should be `j += 1`
  - Fixed sort must produce the same output as Python's built-in sorted()
  - Must handle: empty [], single [1], duplicates [1,1,1], negatives [-3,-1,0,2], large lists
- **Verification tests:**
  1. Run the fixed sort on a known input: [3,1,4,1,5,9,2,6] should give [1,1,2,3,4,5,6,9]
  2. Compare against sorted() for 100 random lists
  3. Test empty list: merge_sort([]) == []
  4. Test single element: merge_sort([42]) == [42]
  5. Test all duplicates: merge_sort([5,5,5,5]) == [5,5,5,5]
  6. Test negatives: merge_sort([-3,0,-1,2]) == [-3,-1,0,2]
  7. Test already sorted: merge_sort([1,2,3,4]) == [1,2,3,4]
  8. Test reverse sorted: merge_sort([4,3,2,1]) == [1,2,3,4]
  9. Performance test: sort 1M random integers in under 30 seconds
- **Likely failure modes:**
  - Primary doesn't find the actual bug (fixes something else)
  - Primary finds the bug but introduces a new one
  - Test suite doesn't cover all required cases
  - Performance test not included or fails on 1M elements

### Phase 2 (Execution)

The adversary should:
1. Read the diff to confirm the fix changes `i += 1` to `j += 1` in the else branch
2. Run the test suite: `python3 -m pytest test_sort.py -v` or `python3 test_sort.py`
3. Independently test the fixed function:
   ```python
   python3 -c "
   from sort import merge_sort
   assert merge_sort([3,1,4,1,5,9,2,6]) == [1,1,2,3,4,5,6,9]
   assert merge_sort([]) == []
   assert merge_sort([1]) == [1]
   assert merge_sort([5,5,5]) == [5,5,5]
   assert merge_sort([-3,0,-1,2]) == [-3,-1,0,2]
   print('All basic tests passed')
   "
   ```
4. Run a stress test:
   ```python
   python3 -c "
   import random, time
   from sort import merge_sort
   data = [random.randint(-10**6, 10**6) for _ in range(10**6)]
   start = time.time()
   result = merge_sort(data)
   elapsed = time.time() - start
   assert result == sorted(data), 'Sort mismatch!'
   print(f'1M elements sorted in {elapsed:.2f}s')
   assert elapsed < 30, f'Too slow: {elapsed:.2f}s'
   "
   ```
5. Verify the test suite covers all required cases (empty, single, duplicates, negatives, large)

### Expected Findings

If done correctly: PASS with 0 Critical, 0 Major.

Common issues:
- **Critical:** Primary "fixed" the wrong line — sort still produces wrong output
- **Major:** Test suite missing required cases (e.g., no 1M element test)
- **Major:** Fix introduced a new bug (e.g., wrong comparison operator)
- **Minor:** Recursion depth issue on very large lists (Python default is 1000; 1M elements needs ~20 levels so should be fine)

## How to Run

```bash
# This scenario requires a Claude Code session. To test manually:
# 1. Create a directory with the buggy sort.py
# 2. Start Claude Code: claude
# 3. Give it the task above
# 4. After it completes, run /crucible-verify
# 5. Check .crucible/report.md

# Quick verification that the bug exists in the original:
python3 -c "
def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            i += 1  # BUG
    result.extend(left[i:])
    result.extend(right[j:])
    return result

# This will produce wrong output or hang
try:
    result = merge([1,3,5], [2,4,6])
    print(f'Buggy merge result: {result}')
    print(f'Expected:           [1, 2, 3, 4, 5, 6]')
    print(f'Bug confirmed: {result != [1,2,3,4,5,6]}')
except IndexError as e:
    print(f'Bug causes crash: {e}')
"
```
