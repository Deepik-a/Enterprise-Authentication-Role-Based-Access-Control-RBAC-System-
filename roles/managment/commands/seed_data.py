# BaseCommand allows us to create custom Django terminal commands.
from django.core.management.base import BaseCommand

# Import the database models.
from roles.models import Module, Permission, Role


# Django identifies this class as a custom management command.
class Command(BaseCommand):

    # Django automatically executes handle() when we run the command.
    def handle(self, *args, **options):

        # Define modules and the actions allowed inside each module.
        modules_data = {
            'User Management': ['view', 'create', 'edit', 'delete'],
            'Role Management': ['view', 'create', 'edit', 'delete'],
            'Reports': ['view', 'export'],
            'Settings': ['view', 'edit'],
            'Products': ['view', 'create', 'edit', 'delete'],
            'Orders': ['view', 'create', 'edit', 'cancel'],
        }

        # Store all created permissions in a list.
        all_permissions = []

        # Loop through each module and its actions.
        for module_name, actions in modules_data.items():

            # Create the module if it doesn't exist.
            # If it already exists, retrieve the existing record.
            module, _ = Module.objects.get_or_create(name=module_name)

            # Loop through actions like view, create, edit and delete.
            for action in actions:

                # Generate a unique permission name.
                # Example: user_management_view
                codename = f"{module_name.lower().replace(' ', '_')}_{action}"

                # Create the permission if it doesn't exist.
                perm, _ = Permission.objects.get_or_create(
                    module=module,
                    action=action,
                    codename=codename
                )

                # Add the permission object to our list.
                all_permissions.append(perm)

        # Create the Super Admin role if it doesn't exist.
        super_admin, _ = Role.objects.get_or_create(name='Super Admin')

        # Assign every available permission to Super Admin.
        super_admin.permissions.set(all_permissions)

        # Create the Admin role if it doesn't exist.
        admin, _ = Role.objects.get_or_create(name='Admin')

        # Get permissions belonging to User Management and Role Management.
        admin_perms = Permission.objects.filter(
            module__name__in=['User Management', 'Role Management']
        )

        # Assign those permissions to Admin.
        admin.permissions.set(admin_perms)

        # Additional roles like Manager, Employee and Customer
        # can be created and assigned their respective permissions here.

        # Display a success message in the terminal.
        self.stdout.write("Seed data created!")