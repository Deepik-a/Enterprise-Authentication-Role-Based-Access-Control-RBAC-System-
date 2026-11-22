"""Central RBAC rules. Every permission decision in the API goes through here."""

from roles.models import Permission, Role


def is_super_admin(user):
    """Super Admin is identified by the role's stable `code`, never by its name."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.roles.filter(code=Role.SUPER_ADMIN, is_active=True).exists()


def get_permission_codes(user):
    """Set of permission codenames the user holds through active roles."""
    if not user or not user.is_authenticated or not user.is_active:
        return set()
    if is_super_admin(user):
        return set(Permission.objects.values_list("codename", flat=True))
    return set(
        Permission.objects.filter(roles__users=user, roles__is_active=True)
        .values_list("codename", flat=True)
        .distinct()
    )


def has_permission(user, codename):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if is_super_admin(user):
        return True
    return user.roles.filter(is_active=True, permissions__codename=codename).exists()


def get_data_scope(user):
    """Widest data scope across the user's active roles."""
    if is_super_admin(user):
        return Role.SCOPE_ALL
    scopes = user.roles.filter(is_active=True).values_list("data_scope", flat=True)
    best = Role.SCOPE_OWN
    for scope in scopes:
        if Role.SCOPE_RANK.get(scope, 0) > Role.SCOPE_RANK[best]:
            best = scope
    return best


def role_permission_codes(roles):
    return set(
        Permission.objects.filter(roles__in=roles).values_list("codename", flat=True).distinct()
    )


def can_manage_user(actor, target):
    """An actor may only manage users whose privileges they fully hold.

    Stops an Admin from editing, deactivating, resetting the password of,
    or changing the roles of a Super Admin.
    """
    if is_super_admin(actor):
        return True
    if is_super_admin(target):
        return False
    return get_permission_codes(target) <= get_permission_codes(actor)


def check_role_assignment(actor, target, roles):
    """Return an error message if `actor` may not give `target` exactly `roles`, else None."""
    if actor.pk == target.pk:
        return "You cannot change your own roles."
    if not can_manage_user(actor, target):
        return "You cannot change the roles of a user with more privileges than you."
    if any(role.code == Role.SUPER_ADMIN for role in roles) and not is_super_admin(actor):
        return "Only a Super Admin can grant the Super Admin role."
    if not is_super_admin(actor):
        missing = role_permission_codes(roles) - get_permission_codes(actor)
        if missing:
            return "You can only assign roles whose permissions you hold. Missing: " + ", ".join(sorted(missing))
    return None


def check_permission_grant(actor, permission_codes):
    """Return an error message if `actor` may not grant these permissions, else None."""
    if is_super_admin(actor):
        return None
    missing = set(permission_codes) - get_permission_codes(actor)
    if missing:
        return "You can only grant permissions you hold. Missing: " + ", ".join(sorted(missing))
    return None
