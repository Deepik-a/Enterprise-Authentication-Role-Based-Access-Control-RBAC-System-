from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import HasModulePermission

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API for audit log entries."""
    queryset = AuditLog.objects.select_related('actor', 'content_type').all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    permission_map = {'list': 'auditlog_view', 'retrieve': 'auditlog_view'}
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['action', 'actor', 'content_type']
