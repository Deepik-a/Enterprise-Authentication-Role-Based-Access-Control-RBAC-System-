from rest_framework.permissions import BasePermission

from accounts.rbac import has_permission


class HasModulePermission(BasePermission):
    """Deny-by-default module permission check.

    Views declare what each action needs, either:
      * `permission_map = {"list": "orders_view", "cancel": "orders_cancel", ...}`
        (ViewSets; every action, including custom @action ones, must be listed), or
      * `required_permission = "reports_view"` (plain APIViews).

    If an action has no declared permission the request is **denied**, so a
    newly added action is never exposed by accident.
    """

    message = "You do not have permission to perform this action."

    def get_required_permission(self, request, view):
        permission_map = getattr(view, "permission_map", None)
        if permission_map is not None:
            action = getattr(view, "action", None)
            if action is None:
                # APIView-style handler on a mapped view: key by HTTP method.
                action = request.method.lower()
            return permission_map.get(action)
        return getattr(view, "required_permission", None)

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        required = self.get_required_permission(request, view)
        if not required:
            return False
        return has_permission(user, required)
