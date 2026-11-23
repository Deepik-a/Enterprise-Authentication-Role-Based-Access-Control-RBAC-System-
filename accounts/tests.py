"""One APITestCase per test scenario (1-12) from the assignment.

Run with:  python manage.py test
"""

import re
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from accounts.pending_registration import (
    RegistrationRejected, _email_key, _hash_otp as _hash_otp_for_test,
)
from accounts.password_reset import (
    _key as password_reset_key, begin_password_reset, consume_password_reset,
)

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
        cls.roles = {r.code: r for r in Role.objects.exclude(code=None)}
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
        cache.clear()

    def _otp(self, index=-1):
        match = re.search(r'code to .+ is (\d{6})', mail.outbox[index].body)
        self.assertIsNotNone(match)
        return match.group(1)

    @staticmethod
    def _wrong_otp(correct):
        return '000000' if correct != '000000' else '000001'

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
    def _register(self, email='new@test.com', username='newuser', password=PASSWORD):
        return self.client.post('/api/auth/register/', {
            'email': email, 'username': username, 'password': password}, format='json')

    @patch('accounts.views._send_otp_email', side_effect=RuntimeError('SMTP credentials leaked'))
    def test_email_delivery_failure_is_generic_and_clears_pending_signup(self, _send_email):
        res = self._register()
        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.data['error'], 'Could not send the verification code. Please try again later.')
        self.assertNotIn('SMTP credentials leaked', str(res.data))
        self.assertIsNone(cache.get(_email_key('new@test.com')))
        self.assertFalse(User.objects.filter(email='new@test.com').exists())

    def test_resend_email_failure_does_not_expose_smtp_details(self):
        self._register()
        with patch('accounts.views._send_otp_email', side_effect=RuntimeError('private smtp response')):
            response = self.client.post('/api/auth/resend-otp/', {'email': 'new@test.com'}, format='json')
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('private smtp response', str(response.data))
        self.assertIsNone(cache.get(_email_key('new@test.com')))

    @patch('accounts.views._send_otp_email')
    def test_admin_created_user_is_pending_until_email_otp_then_gets_selected_role(self, send_email):
        role = Role.objects.create(name='Auditor', data_scope=Role.SCOPE_OWN)
        client = self.client_for(self.superadmin)
        response = client.post('/api/users/register_with_otp/', {
            'email': 'verified-staff@test.com', 'username': 'verifiedstaff',
            'password': PASSWORD, 'role_ids': [role.id],
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(User.objects.filter(email='verified-staff@test.com').exists())
        otp = send_email.call_args.args[2]
        response = self.client.post('/api/auth/verify-otp/', {
            'email': 'verified-staff@test.com', 'otp': otp,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        created = User.objects.get(email='verified-staff@test.com')
        self.assertEqual(list(created.roles.values_list('name', flat=True)), ['Auditor'])

    @patch('accounts.views._send_otp_email')
    def test_managed_registration_cannot_assign_super_admin(self, _send_email):
        client = self.client_for(self.superadmin)
        response = client.post('/api/users/register_with_otp/', {
            'email': 'forbidden@test.com', 'username': 'forbiddenuser',
            'password': PASSWORD, 'role_ids': [self.roles[Role.SUPER_ADMIN].id],
        }, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(email='forbidden@test.com').exists())

    def test_register_keeps_details_in_cache_until_otp(self):
        res = self._register()
        self.assertEqual(res.status_code, 200)
        self.assertNotIn('otp', res.data)
        self.assertFalse(User.objects.filter(email='new@test.com').exists())

        pending = cache.get(_email_key('new@test.com'))
        self.assertIsNotNone(pending)
        self.assertNotEqual(pending['password'], PASSWORD)
        self.assertTrue(pending['password'].startswith('pbkdf2_'))
        otp = self._otp()
        self.assertNotIn(otp, str(pending))

        _, res = self.login('new@test.com')
        self.assertEqual(res.status_code, 401)

        res = self.client.post('/api/auth/verify-otp/', {
            'email': 'new@test.com', 'otp': self._wrong_otp(otp)}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertFalse(User.objects.filter(email='new@test.com').exists())

        res = self.client.post('/api/auth/verify-otp/', {'email': 'new@test.com', 'otp': otp}, format='json')
        self.assertEqual(res.status_code, 201)
        user = User.objects.get(email='new@test.com')
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual([r.code for r in user.roles.all()], [Role.CUSTOMER])
        self.assertIsNone(cache.get(_email_key('new@test.com')))

        client, res = self.login('new@test.com')
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)
        self.assertNotIn('refresh', res.data)
        cookie = res.cookies['refresh_token']
        self.assertTrue(cookie['httponly'])


        res = self.client.post('/api/auth/verify-otp/', {'email': 'new@test.com', 'otp': otp}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_otp_expiry_does_not_create_a_user(self):
        self._register()
        payload = cache.get(_email_key('new@test.com'))
        payload['expires_at'] = (timezone.now() - timedelta(seconds=5)).isoformat()
        cache.set(_email_key('new@test.com'), payload, timeout=60)

        res = self.client.post('/api/auth/verify-otp/', {
            'email': 'new@test.com', 'otp': self._otp()}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('expired', res.data['error'].lower())
        self.assertFalse(User.objects.filter(email='new@test.com').exists())
        self.assertIsNone(cache.get(_email_key('new@test.com')))

    def test_duplicate_email_and_username_are_rejected(self):
        res = self._register(email='customer@test.com', username='brand-new')
        self.assertEqual(res.status_code, 400)
        self.assertIn('email', res.data)

        res = self._register(email='brand-new@test.com', username='customer')
        self.assertEqual(res.status_code, 400)
        self.assertIn('username', res.data)
        self.assertFalse(User.objects.filter(email='brand-new@test.com').exists())

        self._register()
        res = self._register(email='other@test.com', username='newuser')
        self.assertEqual(res.status_code, 400)
        self.assertIn('username', res.data)

    def test_resend_replaces_the_previous_code(self):
        self._register()
        first = self._otp()
        res = self.client.post('/api/auth/resend-otp/', {'email': 'new@test.com'}, format='json')
        self.assertEqual(res.status_code, 200)
        second = self._otp()
        self.assertNotEqual(first, second)

        res = self.client.post('/api/auth/verify-otp/', {'email': 'new@test.com', 'otp': first}, format='json')
        self.assertEqual(res.status_code, 400)
        res = self.client.post('/api/auth/verify-otp/', {'email': 'new@test.com', 'otp': second}, format='json')
        self.assertEqual(res.status_code, 201)

    def test_register_rejects_weak_password(self):
        res = self.client.post('/api/auth/register/', {
            'email': 'weak@test.com', 'username': 'weak', 'password': '12345678'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('password', res.data)

    def test_unverified_existing_account_cannot_log_in(self):
        user = self.make_user('unverified@test.com')
        user.email_verified = False
        user.save(update_fields=['email_verified'])
        _, res = self.login(user.email)
        self.assertEqual(res.status_code, 401)
        session = self.client_for(user)
        self.assertEqual(session.get('/api/auth/me/').status_code, 401)
        self.assertEqual(self.refresh(session.refresh).status_code, 401)

    @override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:3000'])
    def test_refresh_cookie_rotates(self):
        client, res = self.login('customer@test.com')
        res = client.post('/api/auth/token/refresh/', HTTP_ORIGIN='http://localhost:3000')
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)

    @override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:3000'])
    def test_refresh_cookie_rejects_untrusted_origin(self):
        client, res = self.login('customer@test.com')
        self.assertEqual(res.status_code, 200)
        res = client.post('/api/auth/token/refresh/', HTTP_ORIGIN='https://attacker.example')
        self.assertEqual(res.status_code, 403)

    @override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:3000'])
    def test_refresh_cookie_requires_an_allowlisted_origin(self):
        for origin, expected in [(None, 403), ('https://attacker.example', 403), ('http://localhost:3000', 200)]:
            refresh = str(issue_tokens(self.customer))
            client = APIClient()
            client.cookies['refresh_token'] = refresh
            kwargs = {'HTTP_ORIGIN': origin} if origin else {}
            response = client.post('/api/auth/token/refresh/', {}, format='json', **kwargs)
            self.assertEqual(response.status_code, expected, origin)

    def test_access_token_without_revocation_version_is_rejected(self):
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken.for_user(self.customer)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(client.get('/api/auth/me/').status_code, 401)

    def test_expired_access_token_can_be_refreshed(self):
        refresh = issue_tokens(self.customer)
        expired_access = refresh.access_token
        expired_access.set_exp(from_time=timezone.now() - timedelta(minutes=20))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {expired_access}')
        self.assertEqual(client.get('/api/auth/me/').status_code, 401)

        res = self.refresh(str(refresh))
        self.assertEqual(res.status_code, 200)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {res.data["access"]}')
        self.assertEqual(client.get('/api/auth/me/').status_code, 200)

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

    def test_super_admin_cannot_create_or_grant_another_super_admin(self):
        client = self.client_for(self.superadmin)
        res = client.post(f'/api/users/{self.admin.id}/assign_roles/',
                          {'role_ids': [self.roles[Role.SUPER_ADMIN].id]}, format='json')
        self.assertEqual(res.status_code, 403)
        self.assertFalse(self.admin.roles.filter(code=Role.SUPER_ADMIN).exists())
        response = client.post('/api/users/register_with_otp/', {
            'email': 'another-superadmin@test.com', 'username': 'another-superadmin',
            'password': PASSWORD, 'role_ids': [self.roles[Role.SUPER_ADMIN].id],
        }, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(email='another-superadmin@test.com').exists())

    def test_super_admin_identified_by_code_not_name(self):
        Role.objects.filter(code=Role.SUPER_ADMIN).update(name='Renamed')
        Role.objects.create(name='Super Admin')
        fake = self.make_user('fake@test.com')
        fake.roles.add(Role.objects.get(name='Super Admin'))
        self.assertEqual(self.client_for(fake).get('/api/users/').status_code, 403)
        self.assertEqual(self.client_for(self.superadmin).get('/api/users/').status_code, 200)

    def test_django_superuser_flag_alone_does_not_bypass_application_rbac(self):
        site_admin = self.make_user('site-admin@test.com')
        site_admin.is_superuser = True
        site_admin.is_staff = True
        site_admin.save(update_fields=['is_superuser', 'is_staff'])
        client = self.client_for(site_admin)
        self.assertEqual(client.get('/api/users/').status_code, 403)
        profile = client.get('/api/auth/me/')
        self.assertEqual(profile.status_code, 200)
        self.assertFalse(profile.data['is_super_admin'])
        self.assertNotIn('is_superuser', profile.data)


class Scenario03AdminAccess(RBACTestCase):
    def test_admin_manages_users_and_roles(self):
        client = self.client_for(self.admin)
        self.assertEqual(client.get('/api/users/').status_code, 200)
        res = client.post('/api/users/', {'email': 'x@test.com', 'username': 'x', 'password': PASSWORD}, format='json')
        self.assertEqual(res.status_code, 405)
        self.assertEqual(client.post('/api/roles/', {'name': 'Auditor'}, format='json').status_code, 201)

    def test_admin_can_assign_permissions_they_hold(self):
        client = self.client_for(self.admin)
        role = client.post('/api/roles/', {'name': 'Order Reviewer'}, format='json')
        permission = Permission.objects.get(codename='orders_view')
        res = client.post(f'/api/roles/{role.data["id"]}/assign_permissions/',
                          {'permission_ids': [permission.id]}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Role.objects.get(pk=role.data['id']).permissions.filter(pk=permission.pk).exists())

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
        self.assertEqual(client.post(f'/api/users/{self.employee.id}/assign_roles/',
                                     {'role_ids': [self.roles[Role.SUPER_ADMIN].id]}, format='json').status_code, 403)
        self.assertEqual(client.delete(f'/api/users/{sa}/').status_code, 403)
        self.superadmin.refresh_from_db()
        self.assertTrue(self.superadmin.is_active)

    def test_user_search_filter_and_pagination(self):
        client = self.client_for(self.superadmin)
        for index in range(11):
            User.objects.create_user(
                email=f'list{index}@test.com', username=f'list{index}', password=None,
                is_active=index % 2 == 0,
            )

        first_page = client.get('/api/users/?page=1')
        second_page = client.get('/api/users/?page=2')
        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.data['count'], 17)
        self.assertEqual(len(first_page.data['results']), 10)
        self.assertEqual(len(second_page.data['results']), 7)
        self.assertEqual(client.get('/api/users/?search=customer').data['count'], 2)
        self.assertEqual(client.get(f'/api/users/?roles={self.roles[Role.CUSTOMER].id}').data['count'], 2)
        self.assertEqual(client.get('/api/users/?is_active=true').data['count'], 12)
        self.assertEqual(client.get('/api/users/?is_active=false').data['count'], 5)


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

    def test_manager_audit_logs_are_limited_to_their_team(self):
        content_type = ContentType.objects.get_for_model(User)
        team_log = AuditLog.objects.create(
            action=AuditLog.ACTION_UPDATE, actor=self.employee, content_type=content_type,
            object_id=self.customer.id, object_repr='team customer',
        )
        outside_log = AuditLog.objects.create(
            action=AuditLog.ACTION_UPDATE, actor=self.admin, content_type=content_type,
            object_id=self.superadmin.id, object_repr='outside account',
        )
        response = self.client_for(self.manager).get('/api/auditlogs/')
        self.assertEqual(response.status_code, 200)
        visible_ids = {row['id'] for row in response.data['results']}
        self.assertIn(team_log.id, visible_ids)
        self.assertNotIn(outside_log.id, visible_ids)


class Scenario05EmployeeAccess(RBACTestCase):
    def test_employee_permissions(self):
        client = self.client_for(self.employee)
        self.assertEqual(client.get('/api/products/').status_code, 200)
        res = client.post('/api/products/', {'name': 'Mouse', 'price': '10.00'}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(client.delete(f'/api/products/{res.data["id"]}/').status_code, 403)
        self.assertEqual(client.get('/api/users/').status_code, 403)
        self.assertEqual(client.get('/api/reports/summary/').status_code, 403)
        self.assertEqual(client.get('/api/auditlogs/').status_code, 403)
        self.assertEqual(client.get('/api/roles/').status_code, 403)

    def test_employee_sees_only_own_orders(self):
        client = self.client_for(self.employee)
        self.assertEqual(client.get('/api/orders/').data['count'], 0)
        self.assertEqual(client.get(f'/api/orders/{self.order_c1.id}/').status_code, 404)

    def test_product_edit_requires_products_edit(self):
        employee = self.client_for(self.employee)
        res = employee.patch(f'/api/products/{self.product.id}/', {'name': 'Updated laptop'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Updated laptop')

        customer = self.client_for(self.customer)
        res = customer.patch(f'/api/products/{self.product.id}/', {'name': 'Unauthorized edit'}, format='json')
        self.assertEqual(res.status_code, 403)


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

    def test_otp_only_sent_by_email_and_hashed_in_cache(self):
        res = self.request_reset()
        self.assertNotIn('reset_token', res.data)
        self.assertNotIn('token', res.data)
        self.assertNotIn('otp', res.data)
        self.assertEqual(len(mail.outbox), 1)
        otp = self._otp()
        self.assertNotIn(otp, str(res.data))
        stored = cache.get(password_reset_key(self.customer.email))
        self.assertIsNotNone(stored)
        self.assertNotEqual(stored['otp_hash'], otp)
        self.assertEqual(stored['otp_hash'], _hash_otp_for_test(otp))
        self.assertFalse(OneTimeToken.objects.filter(user=self.customer, purpose=OneTimeToken.PURPOSE_RESET).exists())

    def test_unknown_email_gives_same_response(self):
        known = self.request_reset().data
        unknown = self.request_reset('nobody@test.com').data
        self.assertEqual(known, unknown)
        self.assertEqual(len(mail.outbox), 1)

    @patch('accounts.views._send_otp_email', side_effect=RuntimeError('SMTP unavailable'))
    def test_email_delivery_failure_does_not_reveal_account(self, send_email):
        with self.assertLogs('accounts.views', level='ERROR'):
            known = self.client.post('/api/auth/forgot-password/', {
                'email': self.customer.email}, format='json')
        unknown = self.client.post('/api/auth/forgot-password/', {
            'email': 'nobody@test.com'}, format='json')
        self.assertEqual(known.status_code, 200)
        self.assertEqual(known.data, unknown.data)
        self.assertEqual(send_email.call_count, 1)

    def test_reset_flow(self):
        old_session = self.client_for(self.customer)
        self.request_reset()
        otp = self._otp()

        res = self.client.post('/api/auth/reset-password/', {
            'email': self.customer.email, 'otp': otp, 'new_password': 'password'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password(PASSWORD))

        res = self.client.post('/api/auth/reset-password/', {
            'email': self.customer.email, 'otp': self._wrong_otp(otp), 'new_password': NEW_PASSWORD}, format='json')
        self.assertEqual(res.status_code, 400)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password(PASSWORD))

        res = self.client.post('/api/auth/reset-password/', {
            'email': self.customer.email, 'otp': otp, 'new_password': NEW_PASSWORD}, format='json')
        self.assertEqual(res.status_code, 200)

        res = self.client.post('/api/auth/reset-password/', {
            'email': self.customer.email, 'otp': otp, 'new_password': NEW_PASSWORD}, format='json')
        self.assertEqual(res.status_code, 400)

        self.assertEqual(old_session.get('/api/auth/me/').status_code, 401)
        self.assertEqual(self.refresh(old_session.refresh).status_code, 401)
        self.assertEqual(self.login('customer@test.com', PASSWORD)[1].status_code, 401)
        self.assertEqual(self.login('customer@test.com', NEW_PASSWORD)[1].status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.ACTION_PASSWORD_RESET).exists())

    def test_reset_code_expires_and_is_deleted(self):
        self.request_reset()
        otp = self._otp()
        challenge = cache.get(password_reset_key(self.customer.email))
        challenge['expires_at'] = (timezone.now() - timedelta(seconds=5)).isoformat()
        cache.set(password_reset_key(self.customer.email), challenge, timeout=60)

        res = self.client.post('/api/auth/reset-password/', {
            'email': self.customer.email, 'otp': otp, 'new_password': NEW_PASSWORD}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('expired', res.data['error'].lower())
        self.assertIsNone(cache.get(password_reset_key(self.customer.email)))
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password(PASSWORD))

    def test_reset_code_locks_after_too_many_attempts(self):
        correct_otp = begin_password_reset(self.customer.email)
        wrong_otp = self._wrong_otp(correct_otp)
        for _ in range(5):
            with self.assertRaises(RegistrationRejected):
                consume_password_reset(self.customer.email, wrong_otp)
        self.assertIsNone(cache.get(password_reset_key(self.customer.email)))
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password(PASSWORD))

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
        self.assertEqual(res.status_code, 403)
        res = admin.patch(f'/api/users/{self.employee.id}/', {'password': NEW_PASSWORD}, format='json')
        self.assertEqual(res.status_code, 403)
        self.employee.refresh_from_db()
        self.assertTrue(self.employee.check_password(PASSWORD))


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

    def test_no_user_can_grant_super_admin_through_the_application(self):
        res = self.client_for(self.admin).post(f'/api/users/{self.employee.id}/assign_roles/',
                                               {'role_ids': [self.roles[Role.SUPER_ADMIN].id]}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_malformed_privilege_payloads_fail_with_client_errors(self):
        sa = self.client_for(self.superadmin)
        response = sa.post(f'/api/users/{self.employee.id}/assign_roles/',
                           {'role_ids': [[self.roles[Role.ADMIN].id]]}, format='json')
        self.assertEqual(response.status_code, 400)
        response = sa.post(f'/api/roles/{self.roles[Role.ADMIN].id}/assign_permissions/',
                           {'permission_ids': [[1]]}, format='json')
        self.assertEqual(response.status_code, 400)

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

    def test_role_assignment_cannot_expand_actor_data_scope(self):
        manager_role = self.roles[Role.MANAGER]
        permission = Permission.objects.get(codename='user_management_assign')
        manager_role.permissions.add(permission)
        wide_role = Role.objects.create(name='Wide Product Reader', data_scope=Role.SCOPE_ALL)
        wide_role.permissions.add(Permission.objects.get(codename='products_view'))
        response = self.client_for(self.manager).post(
            f'/api/users/{self.employee.id}/assign_roles/',
            {'role_ids': [wide_role.id]}, format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.employee.roles.filter(pk=wide_role.pk).exists())

    def test_actor_cannot_manage_a_user_with_wider_data_scope(self):
        manager_role = self.roles[Role.MANAGER]
        edit_permission = Permission.objects.get(codename='user_management_edit')
        manager_role.permissions.add(edit_permission)
        wider_role = Role.objects.create(name='Wide User Editor', data_scope=Role.SCOPE_ALL)
        wider_role.permissions.add(edit_permission)
        self.employee.roles.add(wider_role)
        response = self.client_for(self.manager).patch(
            f'/api/users/{self.employee.id}/', {'username': 'altered'}, format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.username, 'employee')

    @patch('accounts.views._send_otp_email')
    def test_managed_user_creation_cannot_assign_wider_data_scope(self, _send_email):
        manager_role = self.roles[Role.MANAGER]
        manager_role.permissions.add(Permission.objects.get(codename='user_management_create'))
        wide_role = Role.objects.create(name='Wide Staff Reader', data_scope=Role.SCOPE_ALL)
        wide_role.permissions.add(Permission.objects.get(codename='products_view'))
        response = self.client_for(self.manager).post('/api/users/register_with_otp/', {
            'email': 'wide-staff@test.com', 'username': 'widestaff', 'password': PASSWORD,
            'role_ids': [wide_role.id],
        }, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(email='wide-staff@test.com').exists())

    def test_can_only_grant_permissions_you_hold(self):
        admin = self.client_for(self.admin)
        role_id = admin.post('/api/roles/', {'name': 'Custom'}, format='json').data['id']
        perm = Permission.objects.get(codename='permission_management_create')
        res = admin.post(f'/api/roles/{role_id}/assign_permissions/', {'permission_ids': [perm.id]}, format='json')
        self.assertEqual(res.status_code, 403)
        res = admin.post('/api/roles/', {'name': 'Wide', 'data_scope': 'all'}, format='json')
        self.assertEqual(res.status_code, 201)
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

    def test_default_roles_editable_and_deletable_by_admin(self):

        sa = self.client_for(self.superadmin)
        manager_role = Role.objects.get(code=Role.MANAGER)
        res = sa.patch(f'/api/roles/{manager_role.id}/', {'name': 'Operations Manager'}, format='json')
        self.assertEqual(res.status_code, 200)
        manager_role.refresh_from_db()
        self.assertEqual(manager_role.name, 'Operations Manager')


        perm = Permission.objects.get(codename='products_create')
        res = sa.post(f'/api/roles/{manager_role.id}/assign_permissions/',
                      {'permission_ids': [perm.id]}, format='json')
        self.assertEqual(res.status_code, 200)


        customer_role = Role.objects.get(code=Role.CUSTOMER)
        res = sa.delete(f'/api/roles/{customer_role.id}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Role.objects.filter(id=customer_role.id).exists())

    def test_super_admin_role_cannot_be_deleted_even_by_super_admin(self):
        sa = self.client_for(self.superadmin)
        sa_role = Role.objects.get(code=Role.SUPER_ADMIN)
        res = sa.delete(f'/api/roles/{sa_role.id}/')
        self.assertEqual(res.status_code, 403)
        self.assertTrue(Role.objects.filter(code=Role.SUPER_ADMIN).exists())

    def test_critical_super_admin_permissions_cannot_be_removed(self):
        sa = self.client_for(self.superadmin)
        sa_role = Role.objects.get(code=Role.SUPER_ADMIN)

        perm = Permission.objects.get(codename='products_view')
        res = sa.post(f'/api/roles/{sa_role.id}/assign_permissions/',
                      {'permission_ids': [perm.id]}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_last_active_super_admin_cannot_be_deactivated_or_deleted(self):

        sa = self.client_for(self.superadmin)
        res = sa.post(f'/api/users/{self.superadmin.id}/toggle_active/')
        self.assertEqual(res.status_code, 400)


        res = sa.delete(f'/api/users/{self.superadmin.id}/')
        self.assertEqual(res.status_code, 400)


        sa2 = self.make_user('sa2@test.com', Role.SUPER_ADMIN)
        sa2_client = self.client_for(sa2)


        res = sa.post(f'/api/users/{sa2.id}/toggle_active/')
        self.assertEqual(res.status_code, 200)
        sa2.refresh_from_db()
        self.assertFalse(sa2.is_active)


        res = sa.delete(f'/api/users/{self.superadmin.id}/')
        self.assertEqual(res.status_code, 400)


        res = sa.post(f'/api/users/{self.superadmin.id}/assign_roles/',
                      {'role_ids': [self.roles[Role.ADMIN].id]}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_seed_command_preserves_administrator_changes(self):
        sa = self.client_for(self.superadmin)
        manager_role = Role.objects.get(code=Role.MANAGER)
        sa.patch(f'/api/roles/{manager_role.id}/', {'name': 'Custom Lead'}, format='json')
        perm = Permission.objects.get(codename='orders_export')
        sa.post(f'/api/roles/{manager_role.id}/assign_permissions/', {'permission_ids': [perm.id]}, format='json')


        seed_rbac()

        manager_role.refresh_from_db()

        self.assertEqual(manager_role.name, 'Custom Lead')

        self.assertEqual(list(manager_role.permissions.values_list('codename', flat=True)), ['orders_export'])


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
