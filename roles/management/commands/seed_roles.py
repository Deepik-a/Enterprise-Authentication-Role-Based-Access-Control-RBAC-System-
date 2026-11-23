"""Management command to seed initial modules, permissions, and the four default roles.

Usage:
    python manage.py seed_roles

Safe to run repeatedly without overwriting administrator changes.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from roles.management.commands.seed_data import seed_rbac


class Command(BaseCommand):
    help = "Seed initial modules, permissions, and the default roles (Super Admin, Manager, Employee, Customer)."

    @transaction.atomic
    def handle(self, *args, **options):
        seed_rbac()
        self.stdout.write(self.style.SUCCESS("Default roles, modules, and permissions seeded successfully."))
