# Kaasb API — Error Code Reference

All error responses follow this structure:

```json
{
  "detail": "Human-readable message",
  "code": "KAASB_AUTH_001",
  "field": "email"
}
```

`field` is only present for validation errors targeting a specific request field.

---

## HTTP Status Code Summary

| Status | Meaning |
|--------|---------|
| 400 | Bad Request — invalid input or business rule violation |
| 401 | Unauthorized — missing or invalid token |
| 403 | Forbidden — valid token but insufficient permissions |
| 404 | Not Found — resource does not exist |
| 409 | Conflict — duplicate resource |
| 422 | Validation Error — Pydantic schema mismatch (field-level) |
| 429 | Too Many Requests — rate limit exceeded |
| 500 | Internal Server Error — unexpected failure |
| 502 | Bad Gateway — external service (Stripe, Qi Card, Wise) failure |

---

## Authentication Errors (KAASB_AUTH_*)

| Code | Status | Message | Cause | Resolution |
|------|--------|---------|-------|-----------|
| KAASB_AUTH_001 | 401 | Invalid credentials | Wrong email/password | Check credentials |
| KAASB_AUTH_002 | 401 | Token expired | Access token past 30-min TTL | Call `/auth/refresh` |
| KAASB_AUTH_003 | 401 | Invalid token | Malformed or tampered JWT | Re-login |
| KAASB_AUTH_004 | 401 | Refresh token invalid | Expired or revoked refresh token | Re-login |
| KAASB_AUTH_005 | 403 | Account suspended | User account suspended by admin | Contact support |
| KAASB_AUTH_006 | 403 | Account deactivated | User self-deactivated account | Contact support |
| KAASB_AUTH_007 | 429 | Too many login attempts | Rate limit: 5 attempts/5 min | Wait 5 minutes |
| KAASB_AUTH_008 | 429 | Too many registrations | Rate limit: 3 attempts/10 min | Wait 10 minutes |

**Example 401 response:**
```json
{
  "detail": "Token has expired",
  "code": "KAASB_AUTH_002"
}
```

---

## User Errors (KAASB_USER_*)

| Code | Status | Message | Cause | Resolution |
|------|--------|---------|-------|-----------|
| KAASB_USER_001 | 404 | User not found | Username/ID doesn't exist | Check the identifier |
| KAASB_USER_002 | 409 | Email already registered | Duplicate email | Use a different email or login |
| KAASB_USER_003 | 409 | Username taken | Duplicate username | Choose a different username |
| KAASB_USER_004 | 400 | Invalid password | Doesn't meet complexity rules | 8+ chars, 1 uppercase, 1 digit, 1 special |
| KAASB_USER_005 | 400 | Wrong current password | Incorrect current password in change-password | Provide correct current password |
| KAASB_USER_006 | 400 | Invalid file type | Avatar upload rejected | Use JPEG, PNG, or WebP |
| KAASB_USER_007 | 400 | File too large | Avatar exceeds 10 MB | Resize to under 10 MB |

---

## Job Errors (KAASB_JOB_*)

| Code | Status | Message | Cause | Resolution |
|------|--------|---------|-------|-----------|
| KAASB_JOB_001 | 404 | Job not found | Job ID doesn't exist or is deleted | Verify the job ID |
| KAASB_JOB_002 | 403 | Not job owner | Updating a job you don't own | Only the posting client can modify |
| KAASB_JOB_003 | 400 | Job already closed | Trying to close an already-closed job | No action needed |
| KAASB_JOB_004 | 400 | Cannot delete active job | Job has an active contract | Complete or cancel the contract first |
| KAASB_JOB_005 | 403 | Client role required | Freelancer trying to post a job | Switch to a client account |

---

## Proposal Errors (KAASB_PROP_*)

| Code | Status | Message | Cause | Resolution |
|------|--------|---------|-------|-----------|
| KAASB_PROP_001 | 404 | Proposal not found | Proposal ID doesn't exist | Verify the proposal ID |
| KAASB_PROP_002 | 409 | Already proposed | Duplicate proposal on same job | One proposal per job per freelancer |
| KAASB_PROP_003 | 403 | Freelancer role required | Client trying to submit a proposal | Use a freelancer account |
| KAASB_PROP_004 | 400 | Job is closed | Proposing on a closed/filled job | Look for open jobs |
| KAASB_PROP_005 | 400 | Cannot update non-pending proposal | Editing after shortlist/accept/reject | Create a new proposal if needed |
| KAASB_PROP_006 | 403 | Not proposal owner | Updating another user's proposal | Check the proposal ID |
| KAASB_PROP_007 | 403 | Not job owner | Responding to proposal on job you don't own | — |

---

## Contract Errors (KAASB_CONTRACT_*)

| Code | Status | Message | Cause | Resolution |
|------|--------|---------|-------|-----------|
| KAASB_CONTRACT_001 | 404 | Contract not found | Contract ID doesn't exist | Verify the contract ID |
| KAASB_CONTRACT_002 | 403 | Not a contract party | Accessing contract you're not part of | Check the contract ID |
| KAASB_CONTRACT_003 | 400 | Contract not active | Modifying a completed/cancelled contract | — |

---

## Milestone Errors (KAASB_MS_*)

| Code | Status | Message | Cause | Resolution |
|------|--------|---------|-------|-----------|
| KAASB_MS_001 | 404 | Milestone not found | Milestone ID doesn't exist | Verify the milestone ID |
| KAASB_MS_002 | 400 | Invalid status transition | e.g. submitting a non-in-progress milestone | Follow the milestone workflow |
| KAASB_MS_003 | 403 | Not milestone freelancer | Only assigned freelancer can start/submit | — |
| KAASB_MS_004 | 403 | Not milestone client | Only client can approve/request-changes | — |
| KAASB_MS_005 | 400 | Escrow not funded | Approving without funded escrow | Fund escrow first |

**Milestone workflow:**
```
pending → in_progress (start) → submitted (submit) → approved/request_changes (review)
                                                                ↓
                                                         in_progress (if changes requested)
```

---

## Payment Errors (KAASB_PAY_*)

| Code | Status | Message | Cause | Resolution |
|------|--------|---------|-------|-----------|
| KAASB_PAY_001 | 400 | Insufficient balance | Payout amount exceeds available balance | Check balance first |
| KAASB_PAY_002 | 400 | Escrow already funded | Funding same milestone twice | Each milestone funded once |
| KAASB_PAY_003 | 400 | Invalid payment method | Unsupported provider | Use `stripe`, `qi_card`, or `wise` |
| KAASB_PAY_004 | 502 | Stripe error | Stripe API failure | Check Stripe status; retry |
| KAASB_PAY_005 | 502 | Qi Card error | Qi Card gateway failure | Check Qi Card sandbox/live status |
| KAASB_PAY_006 | 502 | Wise error | Wise API failure | Check Wise status; retry |
| KAASB_PAY_007 | 400 | Webhook signature invalid | HMAC verification failed | Ensure correct secret key |

---

## Review Errors (KAASB_REV_*)

| Code | Status | Message | Cause | Resolution |
|------|--------|---------|-------|-----------|
| KAASB_REV_001 | 409 | Already reviewed | Duplicate review for same contract | One review per party per contract |
| KAASB_REV_002 | 400 | Contract not completed | Reviewing an active contract | Wait for contract completion |
| KAASB_REV_003 | 403 | Not a contract party | Reviewing a contract you're not part of | — |

---

## Validation Errors (422)

Pydantic validation errors return a list of field-level errors:

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "username"],
      "msg": "String should have at least 3 characters",
      "input": "ab",
      "ctx": { "min_length": 3 }
    },
    {
      "type": "value_error",
      "loc": ["body", "password"],
      "msg": "Password must contain at least one uppercase letter",
      "input": "weakpassword1!"
    }
  ]
}
```

**Common validation errors:**

| Field | Rule | Error |
|-------|------|-------|
| email | Valid email format | `value_error.email` |
| username | 3–50 chars, `[a-zA-Z0-9_-]` only | `string_pattern_mismatch` |
| password | 8–128 chars, uppercase + digit + special | `value_error` |
| primary_role | `client` or `freelancer` | `string_pattern_mismatch` |
| bid_amount | Positive number | `greater_than` |
| rating | 1–5 integer | `less_than_equal` / `greater_than_equal` |

---

## Rate Limit Errors (429)

When rate limited, the response includes headers:

```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1711569600
Retry-After: 300
```

```json
{
  "detail": "Rate limit exceeded. Try again in 300 seconds.",
  "code": "KAASB_AUTH_007"
}
```

**Rate limits by endpoint:**

| Endpoint | Limit | Window |
|---------|-------|--------|
| POST /auth/login | 5 requests | 5 minutes |
| POST /auth/register | 3 requests | 10 minutes |
| PUT /users/password | 5 requests | 5 minutes |
| POST /users/avatar | 10 requests | 1 minute |
| All other API writes | 120 requests | 1 minute |
| All API reads | 120 requests | 1 minute |

**Recommended retry strategy:**
```python
import time

def api_call_with_retry(fn, max_retries=3):
    for attempt in range(max_retries):
        resp = fn()
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 60))
            time.sleep(retry_after)
            continue
        return resp
    raise Exception("Rate limit exceeded after retries")
```

---

## Troubleshooting Common Issues

### "401 Token has expired" after 30 minutes
Call `POST /auth/refresh` with your `refresh_token`. Store the new `access_token`. Refresh tokens last 7 days.

### "422 Unprocessable Entity" on registration
Check password complexity: must contain uppercase letter, digit, and special character (!@#$%^&*).

### "409 Already proposed" on job
Each freelancer can submit one proposal per job. Use `PUT /proposals/{id}` to update an existing proposal.

### "502 External service error" on payments
Stripe, Qi Card, or Wise returned an error. Check their status pages. These errors are automatically logged to Sentry.

### WebSocket connection drops
WebSocket state is per-Gunicorn worker. If you're load-balanced across workers, reconnect and re-authenticate. Redis pub/sub support is planned for v1.1.
