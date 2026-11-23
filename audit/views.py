from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import HasModulePermission
from accounts.rbac import get_data_scope
from roles.models import Role

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API for audit log entries."""
    queryset = AuditLog.objects.select_related('actor', 'content_type').order_by('id')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    permission_map = {'list': 'auditlog_view', 'retrieve': 'auditlog_view'}
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['action', 'actor', 'content_type']

    def get_queryset(self):
        queryset = super().get_queryset()
        scope = get_data_scope(self.request.user)
        if scope == Role.SCOPE_ALL:
            return queryset
        if scope == Role.SCOPE_TEAM:
            return queryset.filter(Q(actor=self.request.user) | Q(actor__manager=self.request.user))
        return queryset.filter(actor=self.request.user)
