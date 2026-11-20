
from rest_framework.permissions import BasePermission #It provides methods such as has_permission() that we can override.

class HasModulePermission(BasePermission): #Does the currently logged-in user have permission to access this API?
    
    def has_permission(self, request, view):#it looks the incoming request and the view it handles
        user = request.user
        if not user.is_authenticated:
            return False
        
        # Super Admin bypasses all checks
        if user.roles.filter(name='Super Admin').exists():
            return True
        
        #If the view doesn't specify a required permission, this custom permission class allows the request.
        required = getattr(view, 'required_permission', None)
        if required is None:
            return True
        
        # Check: does ANY of the user's roles have this permission?
        return user.roles.filter(
            permissions__codename=required,
            is_active=True
        ).exists()