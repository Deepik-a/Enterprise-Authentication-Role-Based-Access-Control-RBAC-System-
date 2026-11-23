"""Central RBAC rules. Every permission decision in the API goes through here."""

from roles.models import Permission, Role


def is_super_admin(user):
    """Super Admin is identified by the role's stable `code`, never by its name."""
    if not user or not user.is_authenticated:
        return False
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
    if is_super_admin(target) or target.is_superuser or target.is_staff:
        return False
    if Role.SCOPE_RANK.get(get_data_scope(target), 0) > Role.SCOPE_RANK.get(get_data_scope(actor), 0):
        return False
    return get_permission_codes(target) <= get_permission_codes(actor)


def is_last_active_super_admin(user):
    """Check if `user` is currently an active Super Admin and is the only active Super Admin in the system."""
    if not user or not user.is_active or not is_super_admin(user):
        return False
    from django.contrib.auth import get_user_model
    User = get_user_model()
    active_sa_count = User.objects.filter(
        roles__code=Role.SUPER_ADMIN, roles__is_active=True, is_active=True,
    ).distinct().count()
    return active_sa_count <= 1


def check_role_assignment(actor, target, roles):
    """Return an error message if `actor` may not give `target` exactly `roles`, else None."""
    if actor.pk == target.pk:
        return "You cannot change your own roles."
    if not can_manage_user(actor, target):
        return "You cannot change the roles of a user with more privileges than you."
    if any(role.code == Role.SUPER_ADMIN for role in roles):
        return "Super Admin accounts can only be created by the seed process."
    if not is_super_admin(actor):
        missing = role_permission_codes(roles) - get_permission_codes(actor)
        if missing:
            return "You can only assign roles whose permissions you hold. Missing: " + ", ".join(sorted(missing))
        actor_scope = Role.SCOPE_RANK.get(get_data_scope(actor), 0)
        if any(Role.SCOPE_RANK.get(role.data_scope, 0) > actor_scope for role in roles):
            return "You cannot assign a role with a wider data scope than your own."
    if target.is_active and is_last_active_super_admin(target):
        has_sa = any(role.code == Role.SUPER_ADMIN for role in roles)
        if not has_sa:
            return "Cannot remove Super Admin role from the last active Super Admin account."
    return None


def check_permission_grant(actor, permission_codes):
    """Return an error message if `actor` may not grant these permissions, else None."""
    if is_super_admin(actor):
        return None
    missing = set(permission_codes) - get_permission_codes(actor)
    if missing:
        return "You can only grant permissions you hold. Missing: " + ", ".join(sorted(missing))
    return None
