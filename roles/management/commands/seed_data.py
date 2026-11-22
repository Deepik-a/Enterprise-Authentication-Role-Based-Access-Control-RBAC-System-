"""Seed modules, permissions, the five system roles and (optionally) demo users.

    python manage.py seed_data          # modules, permissions, roles
    python manage.py seed_data --demo   # + demo users, a team, products and orders

Safe to run repeatedly.
"""

import os
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from roles.models import Module, Permission, Role

# name, slug (permission prefix), frontend route, sidebar order, actions
MODULES = [
    ('User Management', 'user_management', '/users', 10, ['view', 'create', 'edit', 'delete']),
    ('Role Management', 'role_management', '/roles', 20, ['view', 'create', 'edit', 'delete']),
    ('Permission Management', 'permission_management', '/permissions', 30, ['view', 'create', 'edit', 'delete']),
    ('Module Management', 'module_management', '/modules', 40, ['view', 'create', 'edit', 'delete']),
    ('Products', 'products', '/products', 50, ['view', 'create', 'edit', 'delete']),
    ('Orders', 'orders', '/orders', 60, ['view', 'create', 'edit', 'cancel']),
    ('Reports', 'reports', '/reports', 70, ['view', 'export']),
    ('Audit Logs', 'auditlog', '/audit-logs', 80, ['view']),
    ('Settings', 'settings', '', 90, ['view', 'edit']),
]


def perms(*codes):
    return list(codes)


# code, name, data scope, permission codenames ('*' = everything)
ROLES = [
    (Role.SUPER_ADMIN, 'Super Admin', Role.SCOPE_ALL, '*'),
    (Role.ADMIN, 'Admin', Role.SCOPE_ALL, perms(
        'user_management_view', 'user_management_create', 'user_management_edit', 'user_management_delete',
        'role_management_view', 'role_management_create', 'role_management_edit', 'role_management_delete',
        'products_view', 'products_create', 'products_edit', 'products_delete',
        'orders_view', 'orders_create', 'orders_edit', 'orders_cancel',
        'reports_view', 'reports_export',
        'auditlog_view', 'settings_view',
    )),
    (Role.MANAGER, 'Manager', Role.SCOPE_TEAM, perms(
        'user_management_view',
        'products_view',
        'orders_view', 'orders_create', 'orders_edit', 'orders_cancel',
        'reports_view', 'reports_export',
    )),
    (Role.EMPLOYEE, 'Employee', Role.SCOPE_OWN, perms(
        'products_view', 'products_create', 'products_edit',
        'orders_view', 'orders_create',
    )),
    (Role.CUSTOMER, 'Customer', Role.SCOPE_OWN, perms(
        'products_view',
        'orders_view', 'orders_create', 'orders_cancel',
    )),
]

# email, username, role code, manager email
DEMO_USERS = [
    ('superadmin@example.com', 'superadmin', Role.SUPER_ADMIN, None),
    ('admin@example.com', 'admin', Role.ADMIN, None),
    ('manager@example.com', 'manager', Role.MANAGER, None),
    ('employee@example.com', 'employee', Role.EMPLOYEE, 'manager@example.com'),
    ('customer@example.com', 'customer', Role.CUSTOMER, 'manager@example.com'),
    ('customer2@example.com', 'customer2', Role.CUSTOMER, None),
]


class Command(BaseCommand):
    help = "Seed modules, permissions and roles (add --demo for demo users and data)."

    def add_arguments(self, parser):
        parser.add_argument('--demo', action='store_true', help='Also create demo users, products and orders.')

    @transaction.atomic
    def handle(self, *args, **options):
        seed_rbac()
        self.stdout.write(self.style.SUCCESS("Modules, permissions and roles seeded."))
        if options['demo']:
            password = os.environ.get('DEMO_PASSWORD')
            if not password:
                raise CommandError("Set DEMO_PASSWORD in .env before seeding demo users.")
            seed_demo(password)
            self.stdout.write(self.style.SUCCESS(
                "Demo users created: " + ", ".join(email for email, *_ in DEMO_USERS)
                + " (password = DEMO_PASSWORD from .env)"))


def seed_rbac():
    all_permissions = []
    for name, slug, route, order, actions in MODULES:
        module = Module.objects.filter(slug=slug).first() or Module.objects.filter(name=name).first() or Module(name=name)
        module.name, module.slug, module.route, module.order, module.is_system = name, slug, route, order, True
        module.save()
        for action in actions:
            perm, _ = Permission.objects.update_or_create(
                module=module, action=action, defaults={'codename': f'{slug}_{action}'})
            all_permissions.append(perm)

    for code, name, scope, codes in ROLES:
        role = Role.objects.filter(code=code).first() or Role.objects.filter(name=name).first() or Role(name=name)
        role.name, role.code, role.data_scope, role.is_system, role.is_active = name, code, scope, True, True
        role.save()
        if codes == '*':
            role.permissions.set(all_permissions)
        else:
            role.permissions.set(Permission.objects.filter(codename__in=codes))


def seed_demo(password):
    from shop.models import Order, Product

    User = get_user_model()
    users = {}
    for email, username, role_code, _ in DEMO_USERS:
        user, created = User.objects.get_or_create(email=email, defaults={'username': username})
        if created:
            user.set_password(password)
        user.is_active = True
        user.email_verified = True
        user.save()
        user.roles.set([Role.objects.get(code=role_code)])
        users[email] = user
    for email, _, _, manager_email in DEMO_USERS:
        users[email].manager = users.get(manager_email)
        users[email].save(update_fields=['manager'])

    products = []
    for name, price in [('Laptop', '1200.00'), ('Monitor', '250.00'), ('Keyboard', '45.00')]:
        product, _ = Product.objects.get_or_create(name=name, defaults={'price': Decimal(price)})
        products.append(product)

    if not Order.objects.exists():
        for email, product, qty in [
            ('customer@example.com', products[0], 1),
            ('customer@example.com', products[2], 2),
            ('customer2@example.com', products[1], 1),
            ('employee@example.com', products[1], 3),
        ]:
            Order.objects.create(customer=users[email], product=product, quantity=qty, unit_price=product.price)
