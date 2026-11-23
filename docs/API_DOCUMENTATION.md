# API documentation

The API is rooted at `/api/`. The generated OpenAPI 3 specification is in [`openapi.yaml`](openapi.yaml), and Swagger UI is served at `http://localhost:8000/api/docs/` while the backend is running. `/api/schema/` serves the schema. [`postman_collection.json`](postman_collection.json) can be imported into Postman.

## Authentication

Send the short-lived access token in `Authorization: Bearer <access>` for protected endpoints. Login returns an access token and puts the rotating refresh token in an HttpOnly cookie. The refresh endpoint also supports a refresh token in the request body for non-browser clients. See [Authentication and authorization flow](AUTHENTICATION_AUTHORIZATION.md) for rotation, CSRF/origin checks, revocation, and OTP flows.

## Endpoint index

| Area | Endpoints | Access |
|---|---|---|
| Registration and account verification | `POST /api/auth/register/`, `/verify-otp/`, `/resend-otp/`, `/activate/`, `/resend-activation/` | Public, throttled where configured |
| Login and sessions | `POST /api/auth/login/`, `/token/refresh/`, `/logout/`, `/logout-all/`; `GET /api/auth/me/` | Login/refresh public; logout and profile require authentication |
| Password | `POST /api/auth/forgot-password/`, `/reset-password/`, `/change-password/` | Reset request and completion public; change password authenticated |
| Users | `/api/users/` and `/api/users/{id}/` | JWT plus user-management permission; scoped by data scope |
| User actions | `POST /api/users/register_with_otp/`, `/api/users/{id}/assign_roles/`, `/api/users/{id}/toggle_active/` | JWT plus the declared user-management permission and server-side privilege checks |
| Roles | `/api/roles/` and `/api/roles/{id}/` | JWT plus role-management permission |
| Role action | `POST /api/roles/{id}/assign_permissions/` | JWT plus role-management assign/edit permission and privilege checks |
| Permissions | `/api/permissions/` and `/api/permissions/{id}/` | JWT plus permission-management permission |
| Modules | `/api/modules/` and `/api/modules/{id}/` | JWT plus module-management permission |
| Products | `/api/products/` and `/api/products/{id}/` | JWT plus product permission |
| Orders | `/api/orders/` and `/api/orders/{id}/`; `POST /api/orders/{id}/cancel/` | JWT plus order permission; results are data-scoped |
| Reports | `GET /api/reports/summary/`, `/api/reports/export/` | JWT plus `reports_view` or `reports_export`; results are data-scoped |
| Audit logs | `/api/auditlogs/` and `/api/auditlogs/{id}/` | Read-only; JWT plus `auditlog_view`; results are data-scoped |
| Dashboard | `GET /api/dashboard/stats/` | JWT required |

For ViewSets, list and detail support the HTTP methods documented in OpenAPI. The API restricts user creation to the OTP-verification flows; ordinary `POST /api/users/` is intentionally disabled. User edits accept only `username`; role assignment, activation, and email verification use separate guarded operations.

## Pagination, filtering, and search

List response shape and pagination defaults are defined by Django REST Framework settings and shown in the OpenAPI schema. Users support filters `is_active`, `roles`, and `manager`, and search over `email` and `username`. Audit logs support `action`, `actor`, and `content_type` filters. Consult `openapi.yaml` for exact parameter types, request schemas, and response codes; the live Swagger UI reflects the running server version.

## Error handling

Validation errors use DRF's structured error response. Authentication failures generally return `401`; authenticated users lacking permissions receive `403`; missing or out-of-scope objects return `404`. OTP endpoints avoid returning the code in API responses. Password-reset requests use a generic response to avoid account enumeration.
