import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    username = models.CharField(
        max_length=10,
        unique=True,
        validators=[UnicodeUsernameValidator()],
        error_messages={"unique": "A user with that username already exists."},
    )
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)



    email_verified = models.BooleanField(default=True)
    roles = models.ManyToManyField("roles.Role", blank=True, related_name="users")

    manager = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="team_members"
    )

    token_version = models.PositiveIntegerField(default=0)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]


class OneTimeToken(models.Model):
    """Single-use token for activation and legacy password-reset links.

    Only the SHA-256 hash is stored, so a database leak doesn't expose
    usable tokens. Current password-reset challenges use a short-lived cache OTP.
    """

    PURPOSE_RESET = "reset"
    PURPOSE_ACTIVATE = "activate"
    PURPOSE_CHOICES = [(PURPOSE_RESET, "Password reset"), (PURPOSE_ACTIVATE, "Account activation")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="one_time_tokens")
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    LIFETIMES = {
        PURPOSE_RESET: timedelta(hours=1),
        PURPOSE_ACTIVATE: timedelta(days=2),
    }

    @staticmethod
    def hash(raw_token):
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @classmethod
    def issue(cls, user, purpose):
        """Create a token and return the raw value (to be emailed, never stored)."""

        cls.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(used_at=timezone.now())
        raw = secrets.token_urlsafe(32)
        cls.objects.create(
            user=user,
            purpose=purpose,
            token_hash=cls.hash(raw),
            expires_at=timezone.now() + cls.LIFETIMES[purpose],
        )
        return raw

    @classmethod
    def consume(cls, raw_token, purpose):
        """Return the user for a valid token and mark it used, or None."""
        if not raw_token or not isinstance(raw_token, str):
            return None
        token = (
            cls.objects.select_related("user")
            .filter(token_hash=cls.hash(raw_token), purpose=purpose, used_at__isnull=True, expires_at__gt=timezone.now())
            .first()
        )
        if token is None:
            return None
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])
        return token.user

    @classmethod
    def peek(cls, raw_token, purpose):
        """Return the user for a valid token without consuming it."""
        if not raw_token or not isinstance(raw_token, str):
            return None
        token = (
            cls.objects.select_related("user")
            .filter(token_hash=cls.hash(raw_token), purpose=purpose, used_at__isnull=True, expires_at__gt=timezone.now())
            .first()
        )
        return token.user if token else None
