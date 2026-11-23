from django.contrib.contenttypes.models import ContentType

from .models import AuditLog


def log_action(actor, action, obj, changes=None):
    """Record who did what to which object. Call after the change succeeds."""
    if actor is not None and not getattr(actor, "is_authenticated", False):
        actor = None
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        content_type=ContentType.objects.get_for_model(obj.__class__),
        object_id=obj.pk,
        object_repr=str(obj)[:200],
        changes=changes,
    )
