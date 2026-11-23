# Security test results

Run date: 2026-11-23.

## Backend

Command: `python manage.py test -v 1`.

Result: **70 tests passed, 0 failed.** Django system checks passed during the run.

| Security area | Result |
|---|---|
| Password hashing, validation, email OTP registration and password reset | Pass |
| Short-lived access tokens, refresh rotation, refresh-token revocation, token-version enforcement | Pass |
| Cookie refresh CSRF checks for missing, untrusted, and allowlisted origins | Pass |
| Role-based API access for Super Admin, Admin, Manager, Employee, and Customer | Pass |
| Scoped user, order, and audit-log access; IDOR checks | Pass |
| Permission updates take effect without re-login | Pass |
| Disabled users lose protected-resource and refresh access | Pass |
| Self-role changes, Super Admin grants, wider data-scope grants, malformed privilege payloads | Pass |
| Sensitive role protections in API and Django admin | Pass |

Additional checks: `python manage.py check` passed; `python manage.py makemigrations --check --dry-run` reported no model changes requiring migrations.

## Frontend

Command: `npm test -- --watchAll=false`.

Result: **7 tests passed.** They cover unauthenticated redirects, direct-route permission denial, rendering for an authorized user, backend-fed permissions, dynamic sidebar links, and permission-based product actions.

Command: `npm run build`.

Result: production build compiled successfully.

## Scope notes

- Restricted API behavior was exercised through DRF's API test client against the same HTTP endpoints called by Postman; Postman itself was not run.
- Email delivery was exercised with Django's in-memory test email backend; a live SMTP provider was not tested.
- React route protection was unit tested; a full manual browser walkthrough was not performed.
