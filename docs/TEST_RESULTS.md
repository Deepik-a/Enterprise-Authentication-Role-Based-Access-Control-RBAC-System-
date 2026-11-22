# Test results

Command: `python manage.py test -v 2` (Django test runner, SQLite test database).

**Result: 41 tests, all passed.** Run date: 2026-11-21.

The tests were also checked against the original bug: with the old fail-open permission check put back, 5 of the 7 privilege-escalation tests fail.

| Scenario | Test | Result |
|---|---|---|
| 1. Registration, activation and login | `test_login_is_throttled` | ✅ pass |
| 1. Registration, activation and login | `test_refresh_cookie_rotates` | ✅ pass |
| 1. Registration, activation and login | `test_register_rejects_weak_password` | ✅ pass |
| 1. Registration, activation and login | `test_register_requires_activation_then_login` | ✅ pass |
| 2. Super Admin has full access | `test_super_admin_can_access_everything` | ✅ pass |
| 2. Super Admin has full access | `test_super_admin_can_grant_super_admin` | ✅ pass |
| 2. Super Admin has full access | `test_super_admin_identified_by_code_not_name` | ✅ pass |
| 3. Admin manages users and roles, but not Super Admin | `test_admin_cannot_manage_permissions_or_modules` | ✅ pass |
| 3. Admin manages users and roles, but not Super Admin | `test_admin_cannot_touch_super_admin` | ✅ pass |
| 3. Admin manages users and roles, but not Super Admin | `test_admin_manages_users_and_roles` | ✅ pass |
| 4. Manager sees only their team | `test_manager_cannot_admin` | ✅ pass |
| 4. Manager sees only their team | `test_manager_sees_only_team` | ✅ pass |
| 4. Manager sees only their team | `test_manager_sees_team_orders_only` | ✅ pass |
| 5. Employee has limited access | `test_employee_permissions` | ✅ pass |
| 5. Employee has limited access | `test_employee_sees_only_own_orders` | ✅ pass |
| 6. Customer is restricted to own data | `test_customer_blocked_from_admin_apis` | ✅ pass |
| 6. Customer is restricted to own data | `test_customer_cannot_place_order_for_someone_else` | ✅ pass |
| 6. Customer is restricted to own data | `test_customer_dashboard_hides_admin_counts` | ✅ pass |
| 6. Customer is restricted to own data | `test_customer_sees_only_own_orders` | ✅ pass |
| 7. Permission changes apply immediately | `test_me_modules_drive_sidebar` | ✅ pass |
| 7. Permission changes apply immediately | `test_permission_changes_apply_without_relogin` | ✅ pass |
| 8. Deactivated users lose access | `test_cannot_deactivate_self` | ✅ pass |
| 8. Deactivated users lose access | `test_deactivated_user_loses_access_and_refresh` | ✅ pass |
| 8. Deactivated users lose access | `test_is_active_not_writable_through_patch` | ✅ pass |
| 9. Logout and token revocation | `test_cannot_logout_another_users_token` | ✅ pass |
| 9. Logout and token revocation | `test_logout_all_revokes_access_tokens` | ✅ pass |
| 9. Logout and token revocation | `test_logout_blacklists_refresh_token` | ✅ pass |
| 10. Forgot / reset password | `test_forgot_password_is_throttled` | ✅ pass |
| 10. Forgot / reset password | `test_reset_flow` | ✅ pass |
| 10. Forgot / reset password | `test_token_only_sent_by_email` | ✅ pass |
| 10. Forgot / reset password | `test_unknown_email_gives_same_response` | ✅ pass |
| 11. Change password | `test_admin_password_update_is_hashed_and_validated` | ✅ pass |
| 11. Change password | `test_change_password` | ✅ pass |
| 12. Privilege escalation is blocked | `test_can_only_assign_roles_within_own_permissions` | ✅ pass |
| 12. Privilege escalation is blocked | `test_can_only_grant_permissions_you_hold` | ✅ pass |
| 12. Privilege escalation is blocked | `test_customer_cannot_make_self_super_admin` | ✅ pass |
| 12. Privilege escalation is blocked | `test_only_super_admin_grants_super_admin` | ✅ pass |
| 12. Privilege escalation is blocked | `test_system_roles_are_protected` | ✅ pass |
| 12. Privilege escalation is blocked | `test_undeclared_action_is_denied` | ✅ pass |
| 12. Privilege escalation is blocked | `test_user_cannot_change_own_roles` | ✅ pass |
| Audit logging | `test_role_and_user_changes_are_logged` | ✅ pass |
