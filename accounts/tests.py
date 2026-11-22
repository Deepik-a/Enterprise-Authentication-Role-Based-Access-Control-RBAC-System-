"""One APITestCase per test scenario (1-12) from the assignment.

Run with:  python manage.py test
"""

import re
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from accounts.models import OneTimeToken
from accounts.permissions import HasModulePermission
from accounts.tokens import issue_tokens
from audit.models import AuditLog
from roles.management.commands.seed_data import seed_rbac
from roles.models import Module, Permission, Role
from shop.models import Order, Product

User = get_user_model()
PASSWORD = 'Str0ng!Passw0rd#1'
NEW_PASSWORD = 'An0ther!Strong#Pw2'


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RBACTestCase(APITestCase):
    """Seeds the real roles/permissions and one user per role."""

    @classmethod
    def setUpTestData(cls):
        seed_rbac()
        cls.roles = {r.code: r for r in Role.objects.filter(is_system=True)}
        cls.superadmin = cls.make_user('superadmin@test.com', Role.SUPER_ADMIN)
        cls.admin = cls.make_user('admin@test.com', Role.ADMIN)
        cls.manager = cls.make_user('manager@test.com', Role.MANAGER)
        cls.employee = cls.make_user('employee@test.com', Role.EMPLOYEE, manager=cls.manager)
        cls.customer = cls.make_user('customer@test.com', Role.CUSTOMER, manager=cls.manager)
        cls.customer2 = cls.make_user('customer2@test.com', Role.CUSTOMER)
        cls.product = Product.objects.create(name='Laptop', price='100.00')
        cls.order_c1 = Order.objects.create(customer=cls.customer, product=cls.product, quantity=1, unit_price='100.00')
        cls.order_c2 = Order.objects.create(customer=cls.customer2, product=cls.product, quantity=2, unit_price='100.00')

    @classmethod
    def make_user(cls, email, role_code=None, manager=None):
        user = User.objects.create_user(email=email, username=email.split('@')[0], password=PASSWORD, manager=manager)
        if role_code:
            user.roles.add(Role.objects.get(code=role_code))
        return user

    def setUp(self):
        cache.clear()  # throttling counters

    def client_for(self, user):
        """An API client authenticated with a real JWT for `user`."""
        client = APIClient()
        refresh = issue_tokens(user)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        client.refresh = str(refresh)
        return client

    def login(self, email, password=PASSWORD, client=None):
        client = client or APIClient()
        return client, client.post('/api/auth/login/', {'email': email, 'password': password}, format='json')

    def refresh(self, raw):
        return APIClient().post('/api/auth/token/refresh/', {'refresh': raw}, format='json')


class Scenario01RegistrationActivationLogin(RBACTestCase):
    def test_register_requires_activation_then_login(self):
        res = self.client.post('/api/auth/register/', {
            'email': 'new@test.com', 'username': 'newuser', 'password': PASSWORD}, format='json')
        self.assertEqual(res.status_code, 201)
        user = User.objects.get(email='new@test.com')
        self.assertFalse(user.is_active)
        self.assertTrue(user.password.startswith('pbkdf2_'))  # hashed, never plain text
        self.assertEqual([r.code for r in user.roles.all()], [Role.CUSTOMER])

        _, res = self.login('new@test.com')
        self.assertEqual(res.status_code, 401)

        self.assertEqual(len(mail.outbox), 1)
        token = re.search(r'token=([\w-]+)', mail.outbox[0].body).group(1)
        res = self.client.post('/api/auth/activate/', {'token': token}, format='json')
        self.assertEqual(res.status_code, 200)

        client, res = self.login('new@test.com')
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)
        self.assertNotIn('refresh', res.data)  # refresh token is only in the httpOnly cookie
        cookie = res.cookies['refresh_token']
        self.assertTrue(cookie['httponly'])

        # Activation token is single-use
        res = self.client.post('/api/auth/activate/', {'token': token}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_register_rejects_weak_password(self):
        res = self.client.post('/api/auth/register/', {
            'email': 'weak@test.com', 'username': 'weak', 'password': '12345678'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('password', res.data)

    def test_refresh_cookie_rotates(self):
        client, res = self.login('customer@test.com')
        res = client.post('/api/auth/token/refresh/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)

    def test_login_is_throttled(self):
        for _ in range(5):
            self.login('customer@test.com', 'wrong-password')
        _, res = self.login('customer@test.com')
        self.assertEqual(res.status_code, 429)


class Scenario02SuperAdminFullAccess(RBACTestCase):
    def test_super_admin_can_access_everything(self):
        client = self.client_for(self.superadmin)
        for url in ['/api/users/', '/api/roles/', '/api/permissions/', '/api/modules/',
                    '/api/auditlogs/', '/api/products/', '/api/orders/', '/api/reports/summary/']:
            self.assertEqual(client.get(url).status_code, 200, url)
        res = client.get('/api/orders/')
        self.assertEqual(res.data['count'], 2)

    def test_super_admin_can_grant_super_admin(self):
        client = self.client_for(self.superadmin)
        res = client.post(f'/api/users/{self.admin.id}/assign_roles/',
                          {'role_ids': [self.roles[Role.SUPER_ADMIN].id]}, format='json')
        self.assertEqual(res.status_code, 200)

    def test_super_admin_identified_by_code_not_name(self):
        Role.objects.filter(code=Role.SUPER_ADMIN).update(name='Renamed')
        Role.objects.create(name='Super Admin')  # a fake role with the old name grants nothing
        fake = self.make_user('fake@test.com')
        fake.roles.add(Role.objects.get(name='Super Admin'))
        self.assertEqual(self.client_for(fake).get('/api/users/').status_code, 403)
        self.assertEqual(self.client_for(self.superadmin).get('/api/users/').status_code, 200)


class Scenario03AdminAccess(RBACTestCase):
    def test_admin_manages_users_and_roles(self):
        client = self.client_for(self.admin)
        self.assertEqual(client.get('/api/users/').status_code, 200)
        res = client.post('/api/users/', {'email': 'x@test.com', 'username': 'x', 'password': PASSWORD}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(client.post('/api/roles/', {'name': 'Auditor'}, format='json').status_code, 201)

    def test_admin_cannot_manage_permissions_or_modules(self):
        client = self.client_for(self.admin)
        self.assertEqual(client.get('/api/permissions/').status_code, 403)
        self.assertEqual(client.get('/api/modules/').status_code, 403)

    def test_admin_cannot_touch_super_admin(self):
        client = self.client_for(self.admin)
        sa = self.superadmin.id
        self.assertEqual(client.patch(f'/api/users/{sa}/', {'first_name': 'x'}, format='json').status_code, 403)
        self.assertEqual(client.patch(f'/api/users/{sa}/', {'password': NEW_PASSWORD}, format='json').status_code, 403)
        self.assertEqual(client.post(f'/api/users/{sa}/toggle_active/').status_code, 403)
        self.assertEqual(client.post(f'/api/users/{sa}/assign_roles/', {'role_ids': []}, format='json').status_code, 403)
        self.assertEqual(client.delete(f'/api/users/{sa}/').status_code, 403)
        self.superadmin.refresh_from_db()
        self.assertTrue(self.superadmin.is_active)


class Scenario04ManagerTeamScope(RBACTestCase):
    def test_manager_sees_only_team(self):
        client = self.client_for(self.manager)
        res = client.get('/api/users/')
        self.assertEqual(res.status_code, 200)
        emails = {u['email'] for u in res.data['results']}
        self.assertEqual(emails, {'manager@test.com', 'employee@test.com', 'customer@test.com'})
        self.assertEqual(client.get(f'/api/users/{self.customer2.id}/').status_code, 404)

    def test_manager_sees_team_orders_only(self):
        client = self.client_for(self.manager)
        ids = {o['id'] for o in client.get('/api/orders/').data['results']}
        self.assertEqual(ids, {self.order_c1.id})
        self.assertEqual(client.get(f'/api/orders/{self.order_c2.id}/').status_code, 404)
        res = client.patch(f'/api/orders/{self.order_c1.id}/', {'status': 'approved'}, format='json')
        self.assertEqual(res.status_code, 200)

    def test_manager_cannot_admin(self):
        client = self.client_for(self.manager)
        self.assertEqual(client.post('/api/users/', {'email': 'y@t.com', 'username': 'y', 'password': PASSWORD}, format='json').status_code, 403)
        self.assertEqual(client.get('/api/roles/').status_code, 403)
        self.assertEqual(client.post(f'/api/users/{self.employee.id}/toggle_active/').status_code, 403)


class Scenario05EmployeeAccess(RBACTestCase):
    def test_employee_permissions(self):
        client = self.client_for(self.employee)
        self.assertEqual(client.get('/api/products/').status_code, 200)
        res = client.post('/api/products/', {'name': 'Mouse', 'price': '10.00'}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(client.delete(f'/api/products/{res.data["id"]}/').status_code, 403)
        self.assertEqual(client.get('/api/users/').status_code, 403)
        self.assertEqual(client.get('/api/reports/summary/').status_code, 403)

    def test_employee_sees_only_own_orders(self):
        client = self.client_for(self.employee)
        self.assertEqual(client.get('/api/orders/').data['count'], 0)
        self.assertEqual(client.get(f'/api/orders/{self.order_c1.id}/').status_code, 404)


class Scenario06CustomerRestricted(RBACTestCase):
    def test_customer_blocked_from_admin_apis(self):
        client = self.client_for(self.customer)
        role = self.roles[Role.ADMIN]
        module = Module.objects.get(slug='products')
        checks = [
            client.get('/api/users/'),
            client.get('/api/roles/'),
            client.post('/api/roles/', {'name': 'Hacker'}, format='json'),
            client.post(f'/api/roles/{self.roles[Role.CUSTOMER].id}/assign_permissions/',
                        {'permission_ids': list(Permission.objects.values_list('id', flat=True))}, format='json'),
            client.get('/api/permissions/'),
            client.post('/api/permissions/', {'module': module.id, 'action': 'x', 'codename': 'x'}, format='json'),
            client.get('/api/modules/'),
            client.delete(f'/api/modules/{module.id}/'),
            client.get('/api/auditlogs/'),
            client.delete(f'/api/roles/{role.id}/'),
        ]
        for res in checks:
            self.assertEqual(res.status_code, 403, res.request)
        self.assertTrue(Module.objects.filter(pk=module.pk).exists())
        self.assertFalse(Role.objects.filter(name='Hacker').exists())

    def test_customer_sees_only_own_orders(self):
        client = self.client_for(self.customer)
        ids = {o['id'] for o in client.get('/api/orders/').data['results']}
        self.assertEqual(ids, {self.order_c1.id})
        # IDOR: someone else's order is invisible, not just forbidden
        self.assertEqual(client.get(f'/api/orders/{self.order_c2.id}/').status_code, 404)
        self.assertEqual(client.post(f'/api/orders/{self.order_c2.id}/cancel/').status_code, 404)
        self.assertEqual(client.post(f'/api/orders/{self.order_c1.id}/cancel/').status_code, 200)

    def test_customer_cannot_place_order_for_someone_else(self):
        client = self.client_for(self.customer)
        res = client.post('/api/orders/', {'product': self.product.id, 'quantity': 1,
                                           'customer': self.customer2.id, 'unit_price': '0.01'}, format='json')
        self.assertEqual(res.status_code, 201)
        order = Order.objects.get(pk=res.data['id'])
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(str(order.unit_price), '100.00')

    def test_customer_dashboard_hides_admin_counts(self):
        res = self.client_for(self.customer).get('/api/dashboard/stats/')
        self.assertEqual(res.status_code, 200)
        self.assertNotIn('users', res.data)
        self.assertNotIn('roles', res.data)
        self.assertEqual(res.data['orders'], 1)


class Scenario07DynamicPermissions(RBACTestCase):
    def test_permission_changes_apply_without_relogin(self):
        client = self.client_for(self.customer2)
        self.assertEqual(client.get('/api/reports/summary/').status_code, 403)

        sa = self.client_for(self.superadmin)
        role_id = sa.post('/api/roles/', {'name': 'Report Reader'}, format='json').data['id']
        perm = Permission.objects.get(codename='reports_view')
        sa.post(f'/api/roles/{role_id}/assign_permissions/', {'permission_ids': [perm.id]}, format='json')
        sa.post(f'/api/users/{self.customer2.id}/assign_roles/',
                {'role_ids': [self.roles[Role.CUSTOMER].id, role_id]}, format='json')

        self.assertEqual(client.get('/api/reports/summary/').status_code, 200)
        me = client.get('/api/auth/me/').data
        self.assertIn('reports_view', me['permissions'])
        self.assertIn('/reports', [m['route'] for m in me['modules']])

        sa.patch(f'/api/roles/{role_id}/', {'is_active': False}, format='json')
        self.assertEqual(client.get('/api/reports/summary/').status_code, 403)

    def test_me_modules_drive_sidebar(self):
        me = self.client_for(self.customer).get('/api/auth/me/').data
        routes = {m['route'] for m in me['modules']}
        self.assertEqual(routes, {'/products', '/orders'})


class Scenario08Deactivation(RBACTestCase):
    def test_deactivated_user_loses_access_and_refresh(self):
        victim = self.client_for(self.employee)
        self.assertEqual(victim.get('/api/auth/me/').status_code, 200)

        res = self.client_for(self.admin).post(f'/api/users/{self.employee.id}/toggle_active/')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data['is_active'])

        self.assertEqual(victim.get('/api/auth/me/').status_code, 401)
        self.assertEqual(self.refresh(victim.refresh).status_code, 401)
        _, res = self.login('employee@test.com')
        self.assertEqual(res.status_code, 401)

        self.client_for(self.admin).post(f'/api/users/{self.employee.id}/toggle_active/')
        _, res = self.login('employee@test.com')
        self.assertEqual(res.status_code, 200)

    def test_cannot_deactivate_self(self):
        res = self.client_for(self.admin).post(f'/api/users/{self.admin.id}/toggle_active/')
        self.assertEqual(res.status_code, 400)

    def test_is_active_not_writable_through_patch(self):
        self.client_for(self.admin).patch(f'/api/users/{self.employee.id}/', {'is_active': False}, format='json')
        self.employee.refresh_from_db()
        self.assertTrue(self.employee.is_active)


class Scenario09Logout(RBACTestCase):
    def test_logout_blacklists_refresh_token(self):
        client, res = self.login('customer@test.com')
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {res.data["access"]}')
        refresh = res.cookies['refresh_token'].value
        self.assertEqual(client.post('/api/auth/logout/').status_code, 200)
        self.assertEqual(self.refresh(refresh).status_code, 401)

    def test_cannot_logout_another_users_token(self):
        other = self.client_for(self.customer2)
        attacker = self.client_for(self.customer)
        res = attacker.post('/api/auth/logout/', {'refresh': other.refresh}, format='json')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(self.refresh(other.refresh).status_code, 200)

    def test_logout_all_revokes_access_tokens(self):
        a = self.client_for(self.customer)
        b = self.client_for(self.customer)
        self.assertEqual(a.post('/api/auth/logout-all/').status_code, 200)
        self.assertEqual(b.get('/api/auth/me/').status_code, 401)
        self.assertEqual(self.refresh(b.refresh).status_code, 401)


class Scenario10ForgotResetPassword(RBACTestCase):
    def request_reset(self, email='customer@test.com'):
        res = self.client.post('/api/auth/forgot-password/', {'email': email}, format='json')
        self.assertEqual(res.status_code, 200)
        return res

    def test_token_only_sent_by_email(self):
        res = self.request_reset()
        self.assertNotIn('reset_token', res.data)
        self.assertNotIn('token', res.data)
        self.assertEqual(len(mail.outbox), 1)
        raw = re.search(r'token=([\w-]+)', mail.outbox[0].body).group(1)
        self.assertNotIn(raw, str(res.data))
        # Only a hash is stored in the DB
        stored = OneTimeToken.objects.get(user=self.customer)
        self.assertNotEqual(stored.token_hash, raw)
        self.assertEqual(stored.token_hash, OneTimeToken.hash(raw))

    def test_unknown_email_gives_same_response(self):
        known = self.request_reset().data
        unknown = self.request_reset('nobody@test.com').data
        self.assertEqual(known, unknown)
        self.assertEqual(len(mail.outbox), 1)

    def test_reset_flow(self):
        old_session = self.client_for(self.customer)
        self.request_reset()
        raw = re.search(r'token=([\w-]+)', mail.outbox[0].body).group(1)

        res = self.client.post('/api/auth/reset-password/', {'token': raw, 'new_password': 'password'}, format='json')
        self.assertEqual(res.status_code, 400)  # validators run

        res = self.client.post('/api/auth/reset-password/', {'token': raw, 'new_password': NEW_PASSWORD}, format='json')
        self.assertEqual(res.status_code, 200)

        res = self.client.post('/api/auth/reset-password/', {'token': raw, 'new_password': NEW_PASSWORD}, format='json')
        self.assertEqual(res.status_code, 400)  # single use

        self.assertEqual(old_session.get('/api/auth/me/').status_code, 401)
        self.assertEqual(self.refresh(old_session.refresh).status_code, 401)
        self.assertEqual(self.login('customer@test.com', PASSWORD)[1].status_code, 401)
        self.assertEqual(self.login('customer@test.com', NEW_PASSWORD)[1].status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.ACTION_PASSWORD_RESET).exists())

    def test_forgot_password_is_throttled(self):
        for _ in range(5):
            self.request_reset('nobody@test.com')
        res = self.client.post('/api/auth/forgot-password/', {'email': 'x@test.com'}, format='json')
        self.assertEqual(res.status_code, 429)


class Scenario11ChangePassword(RBACTestCase):
    def test_change_password(self):
        client = self.client_for(self.customer)
        other_session = self.client_for(self.customer)

        res = client.post('/api/auth/change-password/', {'old_password': 'wrong', 'new_password': NEW_PASSWORD}, format='json')
        self.assertEqual(res.status_code, 400)
        res = client.post('/api/auth/change-password/', {'old_password': PASSWORD, 'new_password': 'customer'}, format='json')
        self.assertEqual(res.status_code, 400)

        res = client.post('/api/auth/change-password/', {'old_password': PASSWORD, 'new_password': NEW_PASSWORD}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(other_session.get('/api/auth/me/').status_code, 401)
        self.assertEqual(self.refresh(other_session.refresh).status_code, 401)

        fresh = APIClient()
        fresh.credentials(HTTP_AUTHORIZATION=f'Bearer {res.data["access"]}')
        self.assertEqual(fresh.get('/api/auth/me/').status_code, 200)

    def test_admin_password_update_is_hashed_and_validated(self):
        admin = self.client_for(self.admin)
        res = admin.patch(f'/api/users/{self.employee.id}/', {'password': '123'}, format='json')
        self.assertEqual(res.status_code, 400)
        res = admin.patch(f'/api/users/{self.employee.id}/', {'password': NEW_PASSWORD}, format='json')
        self.assertEqual(res.status_code, 200)
        self.employee.refresh_from_db()
        self.assertNotEqual(self.employee.password, NEW_PASSWORD)
        self.assertTrue(self.employee.check_password(NEW_PASSWORD))


class Scenario12PrivilegeEscalation(RBACTestCase):
    def test_customer_cannot_make_self_super_admin(self):
        client = self.client_for(self.customer)
        res = client.post(f'/api/users/{self.customer.id}/assign_roles/',
                          {'role_ids': [self.roles[Role.SUPER_ADMIN].id]}, format='json')
        self.assertEqual(res.status_code, 403)
        self.assertFalse(self.customer.roles.filter(code=Role.SUPER_ADMIN).exists())
        res = client.post(f'/api/users/{self.customer.id}/toggle_active/')
        self.assertEqual(res.status_code, 403)

    def test_user_cannot_change_own_roles(self):
        res = self.client_for(self.admin).post(f'/api/users/{self.admin.id}/assign_roles/',
                                               {'role_ids': [self.roles[Role.ADMIN].id]}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_only_super_admin_grants_super_admin(self):
        res = self.client_for(self.admin).post(f'/api/users/{self.employee.id}/assign_roles/',
                                               {'role_ids': [self.roles[Role.SUPER_ADMIN].id]}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_can_only_assign_roles_within_own_permissions(self):
        sa = self.client_for(self.superadmin)
        role_id = sa.post('/api/roles/', {'name': 'Module Editor'}, format='json').data['id']
        perm = Permission.objects.get(codename='module_management_edit')
        sa.post(f'/api/roles/{role_id}/assign_permissions/', {'permission_ids': [perm.id]}, format='json')

        admin = self.client_for(self.admin)
        res = admin.post(f'/api/users/{self.employee.id}/assign_roles/', {'role_ids': [role_id]}, format='json')
        self.assertEqual(res.status_code, 403)
        res = admin.post(f'/api/users/{self.employee.id}/assign_roles/',
                         {'role_ids': [self.roles[Role.MANAGER].id]}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.ACTION_ASSIGN_ROLES, object_id=self.employee.id).exists())

    def test_can_only_grant_permissions_you_hold(self):
        admin = self.client_for(self.admin)
        role_id = admin.post('/api/roles/', {'name': 'Custom'}, format='json').data['id']
        perm = Permission.objects.get(codename='permission_management_create')
        res = admin.post(f'/api/roles/{role_id}/assign_permissions/', {'permission_ids': [perm.id]}, format='json')
        self.assertEqual(res.status_code, 403)
        res = admin.post('/api/roles/', {'name': 'Wide', 'data_scope': 'all'}, format='json')
        self.assertEqual(res.status_code, 201)  # admin's own scope is 'all'
        res = self.client_for(self.superadmin).post('/api/roles/', {'name': 'X', 'data_scope': 'bogus'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_system_roles_are_protected(self):
        admin = self.client_for(self.admin)
        sa_role = self.roles[Role.SUPER_ADMIN]
        self.assertEqual(admin.patch(f'/api/roles/{sa_role.id}/', {'name': 'Owned'}, format='json').status_code, 403)
        self.assertEqual(admin.delete(f'/api/roles/{sa_role.id}/').status_code, 403)
        self.assertEqual(admin.post(f'/api/roles/{self.roles[Role.ADMIN].id}/assign_permissions/',
                                    {'permission_ids': []}, format='json').status_code, 403)
        sa = self.client_for(self.superadmin)
        self.assertEqual(sa.delete(f'/api/roles/{sa_role.id}/').status_code, 403)
        self.assertEqual(sa.delete(f'/api/modules/{Module.objects.get(slug="orders").id}/').status_code, 403)

    def test_undeclared_action_is_denied(self):
        perm = HasModulePermission()
        request = SimpleNamespace(user=self.superadmin, method='POST')
        view = SimpleNamespace(action='brand_new_action', permission_map={'list': 'x_view'})
        self.assertFalse(perm.has_permission(request, view))
        self.assertFalse(perm.has_permission(request, SimpleNamespace()))


class AuditLogTests(RBACTestCase):
    def test_role_and_user_changes_are_logged(self):
        sa = self.client_for(self.superadmin)
        role_id = sa.post('/api/roles/', {'name': 'Logged'}, format='json').data['id']
        sa.patch(f'/api/roles/{role_id}/', {'name': 'Logged2'}, format='json')
        sa.delete(f'/api/roles/{role_id}/')
        sa.post(f'/api/users/{self.employee.id}/toggle_active/')
        actions = list(AuditLog.objects.values_list('action', flat=True))
        for action in ['CREATE', 'UPDATE', 'DELETE', 'DEACTIVATE']:
            self.assertIn(action, actions)
        res = sa.get('/api/auditlogs/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['results'][0]['actor_email'], 'superadmin@test.com')
