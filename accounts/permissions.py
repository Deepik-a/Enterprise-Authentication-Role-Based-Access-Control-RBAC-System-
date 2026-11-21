
from rest_framework.permissions import BasePermission #It provides methods such as has_permission() that we can override.

class HasModulePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
            
        # Superuser bypass or Super Admin role bypass
        if user.is_superuser or user.roles.filter(name='Super Admin').exists():
            return True
        
        # If the view doesn't specify a required permission, allow access
        required = getattr(view, 'required_permission', None)
        if required is None:
            return True
        
        # Check: does ANY of the user's roles have this permission?
        return user.roles.filter(
            permissions__codename=required,
            is_active=True
        ).exists()