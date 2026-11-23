# Authentication and authorization flow

## Registration and email verification

1. `POST /api/auth/register/` validates email, username (3–10 characters), and password (at least 8 characters, including an uppercase letter and a special character), in addition to Django's configured checks.
2. The registration payload and a one-way OTP digest are held in the configured cache for `OTP_TTL_SECONDS` (default 600 seconds). The password is hashed before caching; no user row is created yet.
3. The six-digit OTP is sent by email. The API does not return the OTP.
4. `POST /api/auth/verify-otp/` checks expiry and attempt limits, then creates the active, email-verified user and assigns the default Customer role. Managed user registration can specify permitted roles, but cannot grant Super Admin.
5. Failed email delivery clears pending registration data. OTP attempts are limited by `OTP_MAX_ATTEMPTS` (default 5).

## Login, token refresh, and logout

1. `POST /api/auth/login/` accepts email and password. Disabled or unverified accounts cannot authenticate.
2. The response contains an access token. A rotating refresh token is set in an HttpOnly cookie with configured Secure, SameSite, path, and lifetime attributes.
3. Protected requests send the access token in the Bearer authorization header.
4. When the access token expires, the frontend posts to `/api/auth/token/refresh/`. Cookie-based refresh requires an `Origin` in `CORS_ALLOWED_ORIGINS`; otherwise the server rejects the request and clears the cookie. The API also accepts a refresh token in the body for non-cookie clients.
5. Rotation replaces the refresh token. Logout blacklists the current refresh token; logout-all increments the user's token version and blacklists outstanding refresh tokens. Refresh tokens are also checked against account active/verified state and token version.

Every access token includes a token-version claim. `VersionedJWTAuthentication` rejects tokens when the claim does not match the user's current version, so password changes and logout-all revoke existing access tokens as well. Token lifetimes and blacklist configuration are in `backend/settings.py`.

## Password reset and change

Forgot-password requests return a generic message regardless of whether the email belongs to an active account. For an eligible account, a short-lived OTP digest is stored in cache and the OTP is emailed. Reset consumes the OTP, changes the Django password hash, revokes sessions, and records an audit event. Authenticated password change checks the current password, applies Django password validators, rotates the caller into a fresh session, and revokes the previous tokens.

## Authorization checks

Authorization is evaluated by the backend on every protected operation. ViewSets declare permission codenames through `HasModulePermission`; undeclared actions fail closed. `accounts.rbac` resolves permissions from active roles at request time, so updated role permissions apply without a new login. Super Admin is determined by the seeded `super_admin` role code and receives all defined permissions.

Data scope is applied separately from module permission:

| Scope | Visibility |
|---|---|
| `all` | All records in the authorized queryset |
| `team` | The user's own records and applicable direct reports' records |
| `own` | The user's own records |

Role assignment checks prevent self-assignment, granting Super Admin, granting permissions the actor does not hold, granting a wider data scope, and modifying users beyond the actor's authority. User and order querysets are scoped on the server, preventing IDOR access by changing IDs in a URL. Disabled users are rejected by authentication and refresh checks.

The frontend obtains roles, permissions, modules, and scope from `/api/auth/me/`; it uses these values for route, navigation, and action visibility. UI checks are convenience only: backend permission and object-scope checks remain authoritative.

## CSRF and browser security

The access token is sent in the Authorization header rather than ambient cookies. The refresh token is HttpOnly and cookie-authenticated refresh validates the request Origin against the configured allowlist. Django's CSRF middleware is enabled. CORS credentials and allowed origins are configured in settings; deploy with a narrow HTTPS origin allowlist and secure refresh cookies.
