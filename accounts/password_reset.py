"""Short-lived, cache-backed OTP challenges for password resets."""

import hmac
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from accounts.pending_registration import RegistrationRejected, _hash_otp, _new_otp

RESET_PREFIX = "password_reset:email:"


def _key(email):
    return f"{RESET_PREFIX}{email.strip().lower()}"


def begin_password_reset(email):
    otp = _new_otp()
    payload = {
        "otp_hash": _hash_otp(otp),
        "attempts": 0,
        "expires_at": (timezone.now() + timedelta(seconds=settings.OTP_TTL_SECONDS)).isoformat(),
    }
    cache.set(_key(email), payload, timeout=settings.OTP_TTL_SECONDS)
    return otp


def consume_password_reset(email, otp):
    key = _key(email)
    lock_key = f"{key}:lock"
    lock_value = uuid.uuid4().hex
    if not cache.add(lock_key, lock_value, timeout=10):
        raise RegistrationRejected("A reset is already being processed. Please try again.")
    try:
        payload = cache.get(key)
        if payload is None:
            raise RegistrationRejected("Verification code expired or reset not found. Request a new code.")
        expires_at = parse_datetime(payload.get("expires_at", ""))
        if expires_at is None or timezone.now() >= expires_at:
            cache.delete(key)
            raise RegistrationRejected("Verification code has expired. Request a new code.")
        submitted = _hash_otp(str(otp).strip())
        if not hmac.compare_digest(payload["otp_hash"], submitted):
            payload["attempts"] = int(payload.get("attempts", 0)) + 1
            if payload["attempts"] >= int(settings.OTP_MAX_ATTEMPTS):
                cache.delete(key)
                raise RegistrationRejected("Too many incorrect attempts. Request a new code.")
            timeout = max(1, int((expires_at - timezone.now()).total_seconds()))
            cache.set(key, payload, timeout=timeout)
            raise RegistrationRejected("Invalid verification code.")
        cache.delete(key)
        return True
    finally:
        if cache.get(lock_key) == lock_value:
            cache.delete(lock_key)
