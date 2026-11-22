from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.models import OneTimeToken
from accounts.rbac import (
    can_manage_user, check_role_assignment, get_data_scope, get_permission_codes, is_super_admin,
)
from accounts.serializers import RegisterSerializer, UserSerializer, run_password_validators
from accounts.tokens import (
    LoginSerializer, VersionedTokenRefreshSerializer, clear_refresh_cookie, get_refresh_from_request,
    issue_tokens, revoke_user_tokens, set_refresh_cookie,
)
from audit.models import AuditLog
from audit.utils import log_action
from roles.models import Module, Role
from roles.views import AuditedModelViewSet, crud_map

User = get_user_model()

MessageSerializer = inline_serializer('Message', {'message': serializers.CharField()})
AccessSerializer = inline_serializer('Access', {'access': serializers.CharField()})


def _send_link_email(user, subject, path, raw_token, intro):
    link = f"{settings.FRONTEND_URL}{path}?token={raw_token}"
    send_mail(
        subject,
        f"Hi {user.username},\n\n{intro}\n\n{link}\n\nIf you didn't request this, you can ignore this email.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )


def _password_errors(password, user):
    try:
        run_password_validators(password, user)
    except serializers.ValidationError as exc:
        return exc.detail
    return None


# --- registration & activation -------------------------------------------

class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'register'

    @extend_schema(request=RegisterSerializer, responses={201: MessageSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
            customer = Role.objects.filter(code=Role.CUSTOMER).first()
            if customer:
                user.roles.add(customer)
            raw = OneTimeToken.issue(user, OneTimeToken.PURPOSE_ACTIVATE)
        _send_link_email(user, "Activate your account", "/activate", raw,
                         "Click the link below to activate your account:")
        return Response(
            {"message": "Account created. Check your email for the activation link."},
            status=status.HTTP_201_CREATED,
        )


class ActivateAccountView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'activation'

    @extend_schema(request=inline_serializer('Activate', {'token': serializers.CharField()}),
                   responses={200: MessageSerializer})
    def post(self, request):
        user = OneTimeToken.consume(request.data.get('token'), OneTimeToken.PURPOSE_ACTIVATE)
        if user is None:
            return Response({"error": "Invalid or expired activation link."}, status=400)
        user.email_verified = True
        user.is_active = True
        user.save(update_fields=['email_verified', 'is_active'])
        log_action(user, AuditLog.ACTION_ACTIVATE, user, changes={'via': 'email'})
        return Response({"message": "Account activated. You can now log in."})


class ResendActivationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'activation'

    @extend_schema(request=inline_serializer('ResendActivation', {'email': serializers.EmailField()}),
                   responses={200: MessageSerializer})
    def post(self, request):
        user = User.objects.filter(email__iexact=request.data.get('email', ''), email_verified=False).first()
        if user:
            raw = OneTimeToken.issue(user, OneTimeToken.PURPOSE_ACTIVATE)
            _send_link_email(user, "Activate your account", "/activate", raw,
                             "Click the link below to activate your account:")
        return Response({"message": "If the account exists and is not yet activated, a new link was sent."})


class LoginView(TokenObtainPairView):
    """Returns the access token in the body; the refresh token goes in an httpOnly cookie."""

    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    @extend_schema(responses={200: AccessSerializer})
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            refresh = response.data.pop('refresh')
            set_refresh_cookie(response, refresh)
        return response


class RefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=None, responses={200: AccessSerializer})
    def post(self, request):
        raw = get_refresh_from_request(request)
        if not raw:
            return Response({"detail": "No refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = VersionedTokenRefreshSerializer(data={'refresh': raw})
        try:
            serializer.is_valid(raise_exception=True)
        except (TokenError, InvalidToken, AuthenticationFailed) as exc:
            # Expired, blacklisted, revoked, or the user is inactive.
            detail = exc.detail if isinstance(exc, AuthenticationFailed) else str(exc)
            response = Response({"detail": detail}, status=status.HTTP_401_UNAUTHORIZED)
            clear_refresh_cookie(response)
            return response
        data = serializer.validated_data
        response = Response({"access": data['access']})
        if 'refresh' in data:
            set_refresh_cookie(response, data['refresh'])
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: MessageSerializer})
    def post(self, request):
        raw = get_refresh_from_request(request)
        if not raw:
            response = Response({"error": "No refresh token supplied."}, status=status.HTTP_400_BAD_REQUEST)
            clear_refresh_cookie(response)
            return response
        try:
            token = RefreshToken(raw)
        except TokenError:
            response = Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)
            clear_refresh_cookie(response)
            return response
        # Only your own session can be logged out with this endpoint.
        if str(token.get('user_id')) != str(request.user.pk):
            return Response({"error": "This token does not belong to you."}, status=status.HTTP_403_FORBIDDEN)
        token.blacklist()
        response = Response({"message": "Logged out"})
        clear_refresh_cookie(response)
        return response


class LogoutAllView(APIView):
    """Revoke every token of the current user (all devices)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: MessageSerializer})
    def post(self, request):
        revoke_user_tokens(request.user)
        response = Response({"message": "Logged out from all devices"})
        clear_refresh_cookie(response)
        return response


# --- password flows ---------------------------------------------------------

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'
    GENERIC = {"message": "If an account with that email exists, a reset link has been sent."}

    @extend_schema(request=inline_serializer('ForgotPassword', {'email': serializers.EmailField()}),
                   responses={200: MessageSerializer})
    def post(self, request):
        user = User.objects.filter(email__iexact=request.data.get('email', ''), is_active=True).first()
        if user:
            raw = OneTimeToken.issue(user, OneTimeToken.PURPOSE_RESET)
            # The token is delivered by email only, never in the API response.
            _send_link_email(user, "Reset your password", "/reset-password", raw,
                             "Click the link below to choose a new password (valid for 1 hour):")
        return Response(self.GENERIC)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    @extend_schema(request=inline_serializer('ResetPassword', {
        'token': serializers.CharField(), 'new_password': serializers.CharField()}),
        responses={200: MessageSerializer})
    def post(self, request):
        token = request.data.get('token')
        new_password = request.data.get('new_password') or ''
        user = OneTimeToken.peek(token, OneTimeToken.PURPOSE_RESET)
        if user is None or not user.is_active:
            return Response({"error": "Invalid or expired token."}, status=400)
        errors = _password_errors(new_password, user)
        if errors:
            # Token stays valid so the user can try a stronger password.
            return Response({"new_password": errors}, status=400)
        if OneTimeToken.consume(token, OneTimeToken.PURPOSE_RESET) is None:
            return Response({"error": "Invalid or expired token."}, status=400)
        user.set_password(new_password)
        user.save(update_fields=['password'])
        revoke_user_tokens(user)
        log_action(None, AuditLog.ACTION_PASSWORD_RESET, user)
        return Response({"message": "Password reset successful. Please log in again."})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=inline_serializer('ChangePassword', {
        'old_password': serializers.CharField(), 'new_password': serializers.CharField()}),
        responses={200: AccessSerializer})
    def post(self, request):
        user = request.user
        if not user.check_password(request.data.get('old_password') or ''):
            return Response({"error": "Wrong current password"}, status=400)
        new_password = request.data.get('new_password') or ''
        errors = _password_errors(new_password, user)
        if errors:
            return Response({"new_password": errors}, status=400)
        user.set_password(new_password)
        user.save(update_fields=['password'])
        # Kill every other session, then give this client a fresh pair.
        revoke_user_tokens(user)
        log_action(user, AuditLog.ACTION_PASSWORD_CHANGE, user)
        refresh = issue_tokens(user)
        response = Response({"message": "Password changed", "access": str(refresh.access_token)})
        set_refresh_cookie(response, refresh)
        return response


# --- current user -----------------------------------------------------------

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        user = request.user
        permissions = sorted(get_permission_codes(user))
        # A module shows in the menu when the user can view it.
        view_slugs = {code[:-len('_view')] for code in permissions if code.endswith('_view')}
        modules = list(
            Module.objects.filter(slug__in=view_slugs).values('id', 'name', 'slug', 'route', 'order')
        )
        roles = list(user.roles.filter(is_active=True).values_list('name', flat=True))
        if user.is_superuser and not user.roles.filter(code=Role.SUPER_ADMIN).exists():
            roles.append('Super Admin')

        return Response({
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_superuser": user.is_superuser,
            "is_super_admin": is_super_admin(user),
            "roles": roles,
            "permissions": permissions,
            "modules": modules,
            "data_scope": get_data_scope(user),
            "manager": user.manager.email if user.manager else None,
        })


# --- user management -------------------------------------------------------

def scope_users(user, queryset):
    scope = get_data_scope(user)
    if scope == Role.SCOPE_ALL:
        return queryset
    if scope == Role.SCOPE_TEAM:
        return queryset.filter(Q(pk=user.pk) | Q(manager=user))
    return queryset.filter(pk=user.pk)


class UserViewSet(AuditedModelViewSet):
    queryset = User.objects.select_related('manager').prefetch_related('roles').order_by('-id')
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['email', 'username', 'first_name', 'last_name']
    filterset_fields = ['is_active', 'roles', 'manager']
    permission_map = crud_map('user_management', {
        'assign_roles': 'user_management_edit',
        'toggle_active': 'user_management_edit',
    })

    def get_queryset(self):
        # Object-level scoping: users outside your scope are a 404, not a 403.
        return scope_users(self.request.user, super().get_queryset())

    def _check_can_manage(self, target):
        if not can_manage_user(self.request.user, target):
            raise PermissionDenied("You cannot manage a user with more privileges than you.")

    def perform_update(self, serializer):
        self._check_can_manage(serializer.instance)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        self._check_can_manage(instance)
        super().perform_destroy(instance)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            return Response({"error": "You cannot delete your own logged-in account."}, status=400)
        return super().destroy(request, *args, **kwargs)

    @extend_schema(request=inline_serializer('AssignRoles', {'role_ids': serializers.ListField(child=serializers.IntegerField())}),
                   responses={200: MessageSerializer})
    @action(detail=True, methods=['post'])
    def assign_roles(self, request, pk=None):
        target = self.get_object()
        role_ids = request.data.get('role_ids', [])
        if not isinstance(role_ids, list):
            return Response({"role_ids": "Must be a list of role IDs."}, status=400)
        roles = list(Role.objects.filter(id__in=role_ids))
        if len(roles) != len(set(role_ids)):
            return Response({"role_ids": "One or more role IDs do not exist."}, status=400)

        error = check_role_assignment(request.user, target, roles)
        if error:
            raise PermissionDenied(error)

        before = sorted(target.roles.values_list('name', flat=True))
        target.roles.set(roles)
        log_action(request.user, AuditLog.ACTION_ASSIGN_ROLES, target,
                   changes={'before': before, 'after': sorted(r.name for r in roles)})
        return Response({"message": "Roles assigned"})

    @extend_schema(request=None, responses={200: inline_serializer('ActiveState', {'is_active': serializers.BooleanField()})})
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        if user == request.user and user.is_active:
            return Response({"error": "You cannot deactivate your own account."}, status=400)
        self._check_can_manage(user)
        if user.is_superuser and user.is_active and User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
            return Response({"error": "Cannot deactivate the only active superuser account."}, status=400)
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        if not user.is_active:
            # Access tokens fail on the next request (inactive user); refresh tokens are revoked too.
            revoke_user_tokens(user)
        log_action(request.user, AuditLog.ACTION_ACTIVATE if user.is_active else AuditLog.ACTION_DEACTIVATE, user)
        return Response({"is_active": user.is_active})
