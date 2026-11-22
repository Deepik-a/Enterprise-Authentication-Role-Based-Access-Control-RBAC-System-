from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True, default=None)
    object_type = serializers.CharField(source='content_type.model', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'action', 'timestamp', 'actor', 'actor_email', 'content_type',
                  'object_type', 'object_id', 'object_repr', 'changes']
