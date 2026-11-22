from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class AuditLog(models.Model):
    ACTION_CREATE = 'CREATE'
    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'
    ACTION_ASSIGN_ROLES = 'ASSIGN_ROLES'
    ACTION_ASSIGN_PERMISSIONS = 'ASSIGN_PERMISSIONS'
    ACTION_ACTIVATE = 'ACTIVATE'
    ACTION_DEACTIVATE = 'DEACTIVATE'
    ACTION_PASSWORD_CHANGE = 'PASSWORD_CHANGE'
    ACTION_PASSWORD_RESET = 'PASSWORD_RESET'
    ACTION_CHOICES = [
        (ACTION_CREATE, 'Create'),
        (ACTION_UPDATE, 'Update'),
        (ACTION_DELETE, 'Delete'),
        (ACTION_ASSIGN_ROLES, 'Assign roles'),
        (ACTION_ASSIGN_PERMISSIONS, 'Assign permissions'),
        (ACTION_ACTIVATE, 'Activate'),
        (ACTION_DEACTIVATE, 'Deactivate'),
        (ACTION_PASSWORD_CHANGE, 'Password change'),
        (ACTION_PASSWORD_RESET, 'Password reset'),
    ]

    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    # Generic relation to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    # Kept so the entry still reads well after the object is deleted.
    object_repr = models.CharField(max_length=200, blank=True, default='')
    # JSON snapshot of what changed
    changes = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp', '-id']

    def __str__(self):
        return f"{self.actor} {self.action} {self.content_type.model} at {self.timestamp}"
