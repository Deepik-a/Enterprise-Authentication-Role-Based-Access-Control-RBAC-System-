from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.permissions import HasModulePermission
from accounts.rbac import check_permission_grant, get_data_scope, get_permission_codes, is_super_admin
from audit.models import AuditLog
from audit.utils import log_action

from .models import Module, Permission, Role
from .serializers import ModuleSerializer, PermissionSerializer, RoleSerializer


def crud_map(prefix, extra=None):
    """Permission map for a standard ModelViewSet. Extra actions must be listed explicitly."""
    mapping = {
        'list': f'{prefix}_view',
        'retrieve': f'{prefix}_view',
        'create': f'{prefix}_create',
        'update': f'{prefix}_edit',
        'partial_update': f'{prefix}_edit',
        'destroy': f'{prefix}_delete',
    }
    mapping.update(extra or {})
    return mapping


class AuditedModelViewSet(ModelViewSet):
    """ModelViewSet that writes an AuditLog entry for every create/update/delete."""

    permission_classes = [IsAuthenticated, HasModulePermission]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(self.request.user, AuditLog.ACTION_CREATE, instance, changes=_jsonable(serializer.validated_data))

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(self.request.user, AuditLog.ACTION_UPDATE, instance, changes=_jsonable(serializer.validated_data))

    def perform_destroy(self, instance):
        log_action(self.request.user, AuditLog.ACTION_DELETE, instance)
        instance.delete()


def _jsonable(data):
    out = {}
    for key, value in data.items():
        if key == 'password':
            out[key] = '***'
        elif hasattr(value, 'pk'):
            out[key] = value.pk
        elif isinstance(value, (list, tuple)) or hasattr(value, 'all'):
            out[key] = [getattr(v, 'pk', v) for v in value]
        elif isinstance(value, (str, int, float, bool)) or value is None:
            out[key] = value
        else:
            out[key] = str(value)
    return out


CRITICAL_SUPER_ADMIN_PERMISSIONS = {
    'user_management_view', 'user_management_create', 'user_management_edit', 'user_management_delete',
    'role_management_view', 'role_management_create', 'role_management_edit', 'role_management_delete',
    'permission_management_view', 'permission_management_create', 'permission_management_edit', 'permission_management_delete',
    'module_management_view', 'module_management_create', 'module_management_edit', 'module_management_delete',
}


class RoleViewSet(AuditedModelViewSet):
    queryset = Role.objects.prefetch_related('permissions__module').order_by('id')
    serializer_class = RoleSerializer
    permission_map = crud_map('role_management', {
        'assign_permissions': ['role_management_assign', 'role_management_edit'],
    })

    def _check_role_authority(self, role):
        if role.code == Role.SUPER_ADMIN:
            if not is_super_admin(self.request.user):
                raise PermissionDenied("Only an authorized Super Admin can manage the Super Admin role.")
            return

        if not is_super_admin(self.request.user):

            if role.users.filter(pk=self.request.user.pk).exists():
                raise PermissionDenied("You cannot modify or delete a role you hold.")

            role_perms = set(role.permissions.values_list('codename', flat=True))
            actor_perms = get_permission_codes(self.request.user)
            if not role_perms.issubset(actor_perms):
                raise PermissionDenied("You cannot modify or delete a role with permissions beyond your authority.")

    def _check_scope(self, data_scope):

        if data_scope and not is_super_admin(self.request.user):
            if Role.SCOPE_RANK.get(data_scope, 0) > Role.SCOPE_RANK[get_data_scope(self.request.user)]:
                raise PermissionDenied("You cannot grant a wider data scope than your own.")

    def perform_create(self, serializer):
        self._check_scope(serializer.validated_data.get('data_scope', Role.SCOPE_OWN))
        super().perform_create(serializer)

    def perform_update(self, serializer):
        role = serializer.instance
        if role.code == Role.SUPER_ADMIN:
            if not is_super_admin(self.request.user):
                raise PermissionDenied("Only an authorized Super Admin can modify the Super Admin role.")
            if serializer.validated_data.get('is_active') is False:
                raise PermissionDenied("The Super Admin role cannot be deactivated.")
        else:
            self._check_role_authority(role)

        self._check_scope(serializer.validated_data.get('data_scope'))
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if instance.code == Role.SUPER_ADMIN:
            raise PermissionDenied("Super Admin role cannot be deleted.")
        self._check_role_authority(instance)
        super().perform_destroy(instance)

    @action(detail=True, methods=['post'])
    def assign_permissions(self, request, pk=None):
        role = self.get_object()
        if role.code == Role.SUPER_ADMIN:
            if not is_super_admin(request.user):
                raise PermissionDenied("Only an authorized Super Admin can modify the Super Admin role.")
        else:
            self._check_role_authority(role)

        permission_ids = request.data.get('permission_ids', [])
        if not isinstance(permission_ids, list) or any(type(value) is not int for value in permission_ids):
            raise ValidationError({'permission_ids': 'Must be a list of integer permission IDs.'})
        permissions = list(Permission.objects.filter(id__in=permission_ids))
        if len(permissions) != len(set(permission_ids)):
            raise ValidationError({'permission_ids': 'One or more permission IDs do not exist.'})


        if role.code == Role.SUPER_ADMIN:
            missing_critical = CRITICAL_SUPER_ADMIN_PERMISSIONS - {p.codename for p in permissions}
            if missing_critical:
                raise PermissionDenied(f"Critical Super Admin permissions cannot be removed: {', '.join(sorted(missing_critical))}")

        error = check_permission_grant(request.user, [p.codename for p in permissions])
        if error:
            raise PermissionDenied(error)


        if not is_super_admin(request.user) and role.users.filter(pk=request.user.pk).exists():
            raise PermissionDenied("You cannot modify permissions of a role you hold.")

        before = sorted(role.permissions.values_list('codename', flat=True))
        role.permissions.set(permissions)
        after = sorted(p.codename for p in permissions)
        log_action(request.user, AuditLog.ACTION_ASSIGN_PERMISSIONS, role, changes={'before': before, 'after': after})
        return Response({"message": "Permissions assigned"})


class PermissionViewSet(AuditedModelViewSet):
    queryset = Permission.objects.select_related('module').order_by('id')
    serializer_class = PermissionSerializer
    permission_map = crud_map('permission_management')

    def perform_update(self, serializer):
        if serializer.instance.module.is_system:
            raise PermissionDenied("Permissions of system modules cannot be modified.")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if instance.module.is_system:
            raise PermissionDenied("Permissions of system modules cannot be deleted.")
        super().perform_destroy(instance)


class ModuleViewSet(AuditedModelViewSet):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_map = crud_map('module_management')

    def perform_update(self, serializer):
        if serializer.instance.is_system and 'slug' in serializer.validated_data \
                and serializer.validated_data['slug'] != serializer.instance.slug:
            raise PermissionDenied("The slug of a system module cannot be changed.")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if instance.is_system:
            raise PermissionDenied("System modules cannot be deleted.")
        super().perform_destroy(instance)
