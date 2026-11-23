# Test cases and results

The latest recorded run is documented in [`TEST_RESULTS.md`](TEST_RESULTS.md). It reports 70 passing backend tests, 7 passing frontend tests, a successful production build, and a passing Django system check. No failures were recorded.

## Security and functional test coverage

| ID | Test case | Expected result | Recorded result |
|---|---|---|---|
| AUTH-01 | Register with valid fields, then verify using emailed OTP | No user row before OTP; verified user after valid OTP | Pass |
| AUTH-02 | Submit wrong, expired, or over-attempt OTP | Reject verification; do not create the pending user | Pass |
| AUTH-03 | Login with valid credentials and verified active account | Return access token and set refresh cookie | Pass |
| AUTH-04 | Refresh a valid token; then reuse a rotated or revoked token | Rotate valid token; reject revoked/reused token | Pass |
| AUTH-05 | Refresh cookie from an untrusted Origin | Reject and clear cookie | Pass |
| AUTH-06 | Disable account or increment token version | Deny protected access and refresh with prior tokens | Pass |
| AUTH-07 | Request password reset for existing and unknown email | Return generic response; valid OTP changes password and revokes sessions | Pass |
| RBAC-01 | Call protected API without authentication | Reject request | Pass |
| RBAC-02 | Admin attempts Super Admin-only permission/module operations | Deny operation | Pass |
| RBAC-03 | Manager attempts role management without permission | Deny operation | Pass |
| RBAC-04 | Employee/customer attempts an ungranted internal module | Deny operation | Pass |
| RBAC-05 | Attempt to assign Super Admin, modify own role, exceed permission/scope authority | Reject assignment | Pass |
| RBAC-06 | Change a role permission, then make a subsequent authorization request | Enforce updated permission without re-login | Pass |
| DATA-01 | Change a user/order/audit record ID to another user's object | Hide or deny out-of-scope record | Pass |
| DATA-02 | List users, orders, or audit logs under own/team/all scope | Return only records within scope | Pass |
| FRONT-01 | Open protected route without session or permission | Redirect or render unauthorized state | Pass |
| FRONT-02 | Render navigation and product actions for different backend permissions | Show only permitted modules and actions | Pass |

Backend checks use Django REST Framework's API test client against the HTTP endpoints; these are API authorization tests, not a separate Postman execution. Frontend tests are React unit tests. A full manual browser walkthrough and live SMTP delivery are not claimed as completed; see scope notes in `TEST_RESULTS.md`.

## Reproduce the checks

From the project root:

```powershell
.\venv\Scripts\python.exe manage.py test
.\venv\Scripts\python.exe manage.py check
```

From `frontend/`:

```powershell
npm test -- --watchAll=false
npm run build
```
