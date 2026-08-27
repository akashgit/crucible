# Test Scenario: FeatureBench-Style Programming Question

## Task Given to Primary Agent

> Build a REST API rate limiter middleware in Python (using Flask or FastAPI) with:
>
> 1. Token bucket algorithm with configurable rate (requests/second) and burst size
> 2. Per-client rate limiting based on IP address
> 3. HTTP 429 response with Retry-After header when rate limit exceeded
> 4. GET /api/rate-limit/status endpoint showing current bucket state for the caller
> 5. Pagination on a sample GET /api/items endpoint (limit/offset query params, max 100 per page)
>
> Requirements:
> - Rate limit defaults: 10 requests/second, burst of 20
> - Retry-After header value must be in seconds (integer)
> - Pagination must return total count, current page items, and next/prev links
> - All responses must be JSON

## What the Adversary Should Do

### Phase 1 (Planning)

The adversary should identify:
- **Correctness criteria:**
  - Token bucket: allows burst up to limit, then throttles to steady rate
  - Per-client: different IPs get independent buckets
  - 429 response has correct status code and Retry-After header
  - Rate limit status shows tokens remaining
  - Pagination: limit/offset work, max 100 enforced, total count correct
- **Verification tests:**
  1. Start the server
  2. Send 20 rapid requests (should all succeed — burst)
  3. Send 21st request immediately (should get 429)
  4. Check Retry-After header value is reasonable
  5. Wait for refill, send again (should succeed)
  6. Check /api/rate-limit/status response structure
  7. Test pagination: GET /api/items?limit=5&offset=0, check next link
  8. Test pagination boundary: limit=200 should be capped to 100
  9. Test invalid pagination: limit=-1, offset=-1
  10. Test from two different source IPs (or simulate with X-Forwarded-For)
- **Likely failure modes:**
  - Token bucket doesn't refill over time (missing time-based replenishment)
  - Retry-After is a float instead of integer
  - Rate limiter is global, not per-client
  - Pagination doesn't cap at 100
  - Missing total count in pagination response

### Phase 2 (Execution)

The adversary should:
1. Start the server: `python3 app.py` or `uvicorn app:app`
2. Burst test: `for i in $(seq 1 25); do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/items; done`
3. Check 429: parse the response for Retry-After header
4. Rate limit status: `curl http://localhost:8000/api/rate-limit/status`
5. Pagination: `curl "http://localhost:8000/api/items?limit=5&offset=0"` — check JSON structure
6. Overcap: `curl "http://localhost:8000/api/items?limit=200"` — verify limit capped to 100
7. Different IPs: `curl -H "X-Forwarded-For: 1.2.3.4" http://localhost:8000/api/items`
8. Edge cases: empty items, offset beyond total

### Expected Findings

Common issues:
- **Critical:** Rate limiter doesn't actually limit (no enforcement, all requests succeed)
- **Major:** Token bucket has no time-based refill — once exhausted, never recovers
- **Major:** Retry-After header missing or has float value
- **Major:** Pagination returns more than 100 items when limit=200 requested
- **Major:** Rate limit status endpoint not implemented
- **Minor:** No graceful shutdown handler
- **Minor:** Missing CORS headers

## How to Run

```bash
# This scenario requires a Claude Code session. To test manually:
# 1. Create an empty directory
# 2. Start Claude Code: claude
# 3. Give it the task above
# 4. After it completes, run /crucible-verify
# 5. Check .crucible/report.md

# To verify the rate limiter independently (after primary builds it):
# Start server in background
python3 app.py &
SERVER_PID=$!
sleep 2

# Burst test — send 25 rapid requests
echo "=== Burst test ==="
for i in $(seq 1 25); do
    code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/items)
    echo "Request $i: HTTP $code"
done

# Check rate limit status
echo "=== Rate limit status ==="
curl -s http://localhost:8000/api/rate-limit/status | python3 -m json.tool

# Pagination test
echo "=== Pagination ==="
curl -s "http://localhost:8000/api/items?limit=5&offset=0" | python3 -m json.tool

# Cleanup
kill $SERVER_PID
```
