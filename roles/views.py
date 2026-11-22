from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.permissions import HasModulePermission
from accounts.rbac import check_permission_grant, get_data_scope, is_super_admin
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


class RoleViewSet(AuditedModelViewSet):
    queryset = Role.objects.prefetch_related('permissions__module').order_by('id')
    serializer_class = RoleSerializer
    permission_map = crud_map('role_management', {'assign_permissions': 'role_management_edit'})

    def _check_editable(self, role):
        if role.is_system:
            raise PermissionDenied("System roles cannot be modified or deleted.")

    def _check_scope(self, data_scope):
        # A wider data scope is a privilege too: you can't hand out more than you have.
        if data_scope and not is_super_admin(self.request.user):
            if Role.SCOPE_RANK.get(data_scope, 0) > Role.SCOPE_RANK[get_data_scope(self.request.user)]:
                raise PermissionDenied("You cannot grant a wider data scope than your own.")

    def perform_create(self, serializer):
        self._check_scope(serializer.validated_data.get('data_scope', Role.SCOPE_OWN))
        super().perform_create(serializer)

    def perform_update(self, serializer):
        self._check_editable(serializer.instance)
        self._check_scope(serializer.validated_data.get('data_scope'))
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        self._check_editable(instance)
        super().perform_destroy(instance)

    @action(detail=True, methods=['post'])
    def assign_permissions(self, request, pk=None):
        role = self.get_object()
        self._check_editable(role)

        permission_ids = request.data.get('permission_ids', [])
        if not isinstance(permission_ids, list):
            raise ValidationError({'permission_ids': 'Must be a list of permission IDs.'})
        permissions = list(Permission.objects.filter(id__in=permission_ids))
        if len(permissions) != len(set(permission_ids)):
            raise ValidationError({'permission_ids': 'One or more permission IDs do not exist.'})

        error = check_permission_grant(request.user, [p.codename for p in permissions])
        if error:
            raise PermissionDenied(error)
        # Users can't widen the permissions of a role they hold themselves.
        if not is_super_admin(request.user) and role.users.filter(pk=request.user.pk).exists():
            added = {p.pk for p in permissions} - set(role.permissions.values_list('pk', flat=True))
            if added:
                raise PermissionDenied("You cannot add permissions to a role you hold.")

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
