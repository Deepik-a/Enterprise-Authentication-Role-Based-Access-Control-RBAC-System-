"""Pending self-registrations live in the cache (Redis outside tests).

Nothing is written to the User table until the emailed OTP is accepted.
The password is stored only as a Django password hash.
"""

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from accounts.models import User
from roles.models import Role

EMAIL_PREFIX = "pending_registration:email:"
USERNAME_PREFIX = "pending_registration:username:"


class RegistrationRejected(Exception):
    """A registration or OTP step that should be a 400 response."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


def _ttl():
    return int(settings.OTP_TTL_SECONDS)


def _email_key(email):
    return f"{EMAIL_PREFIX}{email}"


def _username_key(username):
    return f"{USERNAME_PREFIX}{username.lower()}"


def _hash_otp(otp):
    return hmac.new(settings.SECRET_KEY.encode(), otp.encode(), hashlib.sha256).hexdigest()


def _new_otp():
    length = int(settings.OTP_LENGTH)
    return f"{secrets.randbelow(10 ** length):0{length}d}"


def _expires_at():
    return timezone.now() + timedelta(seconds=_ttl())


def _is_expired(payload):
    expires_at = parse_datetime(payload.get('expires_at') or '')
    if expires_at is None:
        return True
    if timezone.is_naive(expires_at):
        expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())
    return timezone.now() >= expires_at


def _remaining_seconds(payload):
    expires_at = parse_datetime(payload['expires_at'])
    if timezone.is_naive(expires_at):
        expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())
    return int((expires_at - timezone.now()).total_seconds())


def _store(payload):
    timeout = max(_remaining_seconds(payload), 1)
    cache.set(_email_key(payload['email']), payload, timeout=timeout)
    cache.set(_username_key(payload['username']), payload['email'], timeout=timeout)


def delete_pending(payload):
    cache.delete(_email_key(payload['email']))
    cache.delete(_username_key(payload['username']))


def _reject_if_taken(email, username):
    if User.objects.filter(email__iexact=email).exists():
        raise RegistrationRejected("A user with this email already exists.", field="email")
    if User.objects.filter(username__iexact=username).exists():
        raise RegistrationRejected("A user with this username already exists.", field="username")
    reserved_for = cache.get(_username_key(username))
    if reserved_for and reserved_for != email:
        raise RegistrationRejected("This username is already reserved by a pending registration.", field="username")


def begin_registration(email, username, password, role_ids=None):
    email = email.strip().lower()
    username = username.strip()
    existing = cache.get(_email_key(email))
    _reject_if_taken(email, username)
    if existing and existing.get('username', '').lower() != username.lower():
        cache.delete(_username_key(existing['username']))
    otp = _new_otp()
    payload = {
        'email': email,
        'username': username,
        'password': make_password(password),
        'otp_hash': _hash_otp(otp),
        'attempts': 0,
        'expires_at': _expires_at().isoformat(),
        'role_ids': [int(value) for value in (role_ids or [])],
    }
    _store(payload)
    return otp


def refresh_otp(email):
    email = email.strip().lower()
    payload = cache.get(_email_key(email))
    if payload is None:
        raise RegistrationRejected("Verification code expired or registration not found. Please register again.")
    if _is_expired(payload):
        delete_pending(payload)
        raise RegistrationRejected("Verification code has expired. Please register again.")
    otp = _new_otp()
    payload['otp_hash'] = _hash_otp(otp)
    payload['attempts'] = 0
    payload['expires_at'] = _expires_at().isoformat()
    _store(payload)
    return otp, payload['username']


def verify_and_create(email, otp):
    email = email.strip().lower()
    payload = cache.get(_email_key(email))
    if payload is None:
        raise RegistrationRejected("Verification code expired or registration not found. Please register again.")
    if _is_expired(payload):
        delete_pending(payload)
        raise RegistrationRejected("Verification code has expired. Please register again.")
    submitted = _hash_otp(str(otp).strip())
    if not hmac.compare_digest(payload['otp_hash'], submitted):
        payload['attempts'] = int(payload.get('attempts', 0)) + 1
        if payload['attempts'] >= int(settings.OTP_MAX_ATTEMPTS):
            delete_pending(payload)
            raise RegistrationRejected("Too many incorrect attempts. Please register again.")
        _store(payload)
        raise RegistrationRejected("Invalid verification code.")

    try:
        _reject_if_taken(payload['email'], payload['username'])
    except RegistrationRejected:
        delete_pending(payload)
        raise

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=payload['email'],
                username=payload['username'],
                password=None,
                is_active=True,
                email_verified=True,
            )
            user.password = payload['password']
            user.save(update_fields=['password'])
            customer = Role.objects.filter(code=Role.CUSTOMER).first()
            requested_roles = Role.objects.filter(id__in=payload.get('role_ids', []), is_active=True)
            if payload.get('role_ids'):
                user.roles.set(requested_roles)
            elif customer:
                user.roles.add(customer)
    except IntegrityError:
        delete_pending(payload)
        raise RegistrationRejected("A user with this email or username already exists.")
    delete_pending(payload)
    return user
