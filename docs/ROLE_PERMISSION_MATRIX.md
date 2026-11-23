# Default role and permission matrix

This matrix describes permissions installed by `python manage.py seed_data` for a fresh database. Permissions are stored as data (`Permission` records linked to modules) and roles can be changed by authorized administrators; this is the seeded baseline, not a hardcoded frontend role map. The frontend reads actual permissions from `/api/auth/me/`.

`✓` means the role is seeded with the listed permission. Super Admin is granted all currently defined permissions through its role. A check still requires an active account and remains subject to data scope and object-level rules.

| Module / action | Super Admin | Admin | Manager | Employee | Customer |
|---|:---:|:---:|:---:|:---:|:---:|
| User management: view | ✓ | ✓ | ✓ | — | — |
| User management: create, edit, delete, assign | ✓ | ✓ | — | — | — |
| Role management: view, create, edit, delete, assign | ✓ | ✓ | — | — | — |
| Permission management: view, create, edit, delete | ✓ | — | — | — | — |
| Module management: view, create, edit, delete | ✓ | — | — | — | — |
| Products: view | ✓ | ✓ | ✓ | ✓ | ✓ |
| Products: create, edit | ✓ | ✓ | — | ✓ | — |
| Products: delete, export | ✓ | ✓ | — | — | — |
| Orders: view, create | ✓ | ✓ | ✓ | ✓ | ✓ |
| Orders: edit, cancel, export | ✓ | ✓ | ✓ | — | Cancel only |
| Reports: view, export | ✓ | ✓ | ✓ | — | — |
| Audit logs: view | ✓ | ✓ | ✓ | — | — |
| Audit logs: export | ✓ | ✓ | — | — | — |
| Settings: view, edit | ✓ | ✓ | — | — | — |

## Data scope defaults

| Seeded role | Scope | Effect |
|---|---|---|
| Super Admin | `all` | All authorized records |
| Admin | `all` | All records in granted modules |
| Manager | `team` | Own and direct reports' applicable records |
| Employee | `own` | Own records |
| Customer | `own` | Own orders and permitted customer data |

The effective scope across multiple active roles is the widest active scope. Non-Super-Admin users cannot grant permissions or a data scope beyond their own authority. The Super Admin role can only be created by the seed process; the role-management API prevents ordinary assignment of that role.
