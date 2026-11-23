import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
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
from accounts.pending_registration import RegistrationRejected, begin_registration, refresh_otp, verify_and_create
from accounts.password_reset import begin_password_reset, consume_password_reset
from accounts.rbac import (
    can_manage_user, check_role_assignment, get_data_scope, get_permission_codes, is_last_active_super_admin, is_super_admin,
    role_permission_codes,
)
from accounts.serializers import RegisterSerializer, UserSerializer, VerifyOTPSerializer, run_password_validators
from accounts.tokens import (
    LoginSerializer, VersionedTokenRefreshSerializer, clear_refresh_cookie, get_refresh_from_request,
    issue_tokens, revoke_user_tokens, set_refresh_cookie,
)
from audit.models import AuditLog
from audit.utils import log_action
from roles.models import Module, Role
from roles.views import AuditedModelViewSet, crud_map

User = get_user_model()
logger = logging.getLogger(__name__)

MessageSerializer = inline_serializer('Message', {'message': serializers.CharField()})
AccessSerializer = inline_serializer('Access', {'access': serializers.CharField()})


def _rejected(exc):
    if exc.field:
        return Response({exc.field: [exc.message]}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"error": exc.message}, status=status.HTTP_400_BAD_REQUEST)


def _send_otp_email(email, username, otp, purpose="verify your email"):
    minutes = max(1, settings.OTP_TTL_SECONDS // 60)
    send_mail(
        "Your verification code",
        (
            f"Hi {username},\n\n"
            f"Your code to {purpose} is {otp}.\n\n"
            f"It expires in {minutes} minutes. "
            "If you didn't request this code, you can ignore this email."
        ),
        settings.DEFAULT_FROM_EMAIL,
        [email],
    )


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




class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'register'

    @extend_schema(request=RegisterSerializer, responses={200: MessageSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            otp = begin_registration(
                email=data["email"], username=data["username"], password=data["password"],
            )
        except RegistrationRejected as exc:
            return _rejected(exc)
        except Exception:
            logger.exception("Registration cache write failed")
            return Response(
                {"error": "Registration could not be started. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            _send_otp_email(data["email"], data["username"], otp, "create your account")
        except Exception:
            logger.exception("Registration verification email delivery failed")
            from accounts.pending_registration import delete_pending
            try:
                delete_pending({"email": data["email"], "username": data["username"]})
            except Exception:
                logger.exception("Could not clear pending registration after email failure")
            return Response(
                {"error": "Could not send the verification code. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {"message": "Verification code sent. Enter it to finish creating your account."},
            status=status.HTTP_200_OK,
        )


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'otp'

    @extend_schema(request=VerifyOTPSerializer, responses={201: MessageSerializer})
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = verify_and_create(email=serializer.validated_data["email"], otp=serializer.validated_data["otp"])
        except RegistrationRejected as exc:
            return _rejected(exc)
        except Exception:
            logger.exception("Registration OTP verification failed because a service was unavailable")
            return Response(
                {"error": "Verification is temporarily unavailable. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        log_action(user, AuditLog.ACTION_ACTIVATE, user, changes={'via': 'otp'})
        return Response(
            {"message": "Account created. You can now log in."},
            status=status.HTTP_201_CREATED,
        )


class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'otp'

    @extend_schema(request=inline_serializer('ResendOTP', {'email': serializers.EmailField()}),
                   responses={200: MessageSerializer})
    def post(self, request):
        email = (request.data.get('email') or '').strip()
        if not email:
            return Response({"email": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            otp, username = refresh_otp(email)
        except RegistrationRejected as exc:
            return _rejected(exc)
        except Exception:
            logger.exception("Registration OTP cache read or update failed")
            return Response(
                {"error": "Could not resend the verification code. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            _send_otp_email(email.strip().lower(), username, otp)
        except Exception:
            logger.exception("Registration OTP email delivery failed")
            from accounts.pending_registration import delete_pending
            try:
                delete_pending({'email': email.strip().lower(), 'username': username})
            except Exception:
                logger.exception("Could not clear registration after resend email failure")
            return Response(
                {"error": "Could not send the verification code. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"message": "A new verification code was sent."})


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
            try:
                _send_link_email(user, "Activate your account", "/activate", raw,
                                 "Click the link below to activate your account:")
            except Exception:
                logger.exception("Activation email delivery failed")
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



        raw = request.data.get('refresh')
        cookie_token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not raw and cookie_token:
            origin = request.headers.get('Origin')
            if origin not in settings.CORS_ALLOWED_ORIGINS:
                response = Response({"detail": "Untrusted origin."}, status=status.HTTP_403_FORBIDDEN)
                clear_refresh_cookie(response)
                return response
            raw = cookie_token
        if not raw:
            return Response({"detail": "No refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = VersionedTokenRefreshSerializer(data={'refresh': raw})
        try:
            serializer.is_valid(raise_exception=True)
        except (TokenError, InvalidToken, AuthenticationFailed) as exc:

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




class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'
    GENERIC = {"message": "If an account with that email exists, a verification code has been sent."}

    @extend_schema(request=inline_serializer('ForgotPassword', {'email': serializers.EmailField()}),
                   responses={200: MessageSerializer})
    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            try:
                otp = begin_password_reset(email)
                _send_otp_email(email, user.username, otp, "reset your password")
            except Exception:
                logger.exception("Forgot-password code delivery failed")
                try:
                    from django.core.cache import cache
                    cache.delete(f"password_reset:email:{email}")
                except Exception:
                    pass
                return Response(self.GENERIC)
        return Response(self.GENERIC)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    @extend_schema(request=inline_serializer('ResetPassword', {
        'email': serializers.EmailField(), 'otp': serializers.CharField(max_length=6, min_length=6),
        'new_password': serializers.CharField()}),
        responses={200: MessageSerializer})
    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        otp = request.data.get('otp') or ''
        new_password = request.data.get('new_password') or ''
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is None:
            return Response({"error": "Invalid or expired verification code."}, status=400)
        errors = _password_errors(new_password, user)
        if errors:
            return Response({"new_password": errors}, status=400)
        try:
            consume_password_reset(email, otp)
        except RegistrationRejected:
            return Response({"error": "Invalid or expired verification code."}, status=400)
        except Exception:
            logger.exception("Password reset OTP validation failed because a service was unavailable")
            return Response({"error": "Password reset is temporarily unavailable. Please try again later."}, status=503)
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

        revoke_user_tokens(user)
        log_action(user, AuditLog.ACTION_PASSWORD_CHANGE, user)
        refresh = issue_tokens(user)
        response = Response({"message": "Password changed", "access": str(refresh.access_token)})
        set_refresh_cookie(response, refresh)
        return response




class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        user = request.user
        permissions = sorted(get_permission_codes(user))

        view_slugs = {code[:-len('_view')] for code in permissions if code.endswith('_view')}
        modules = list(
            Module.objects.filter(slug__in=view_slugs).values('id', 'name', 'slug', 'route', 'order')
        )
        roles = list(user.roles.filter(is_active=True).values_list('name', flat=True))

        return Response({
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_super_admin": is_super_admin(user),
            "roles": roles,
            "permissions": permissions,
            "modules": modules,
            "data_scope": get_data_scope(user),
            "manager": user.manager.email if user.manager else None,
        })




def scope_users(user, queryset):
    scope = get_data_scope(user)
    if scope == Role.SCOPE_ALL:
        return queryset
    if scope == Role.SCOPE_TEAM:
        return queryset.filter(Q(pk=user.pk) | Q(manager=user))
    return queryset.filter(pk=user.pk)


class UserViewSet(AuditedModelViewSet):
    queryset = User.objects.select_related('manager').prefetch_related('roles').order_by('id')
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['email', 'username']
    filterset_fields = ['is_active', 'roles', 'manager']
    permission_map = crud_map('user_management', {
        'assign_roles': ['user_management_assign', 'user_management_edit'],
        'toggle_active': 'user_management_edit',
        'register_with_otp': 'user_management_create',
    })

    def get_queryset(self):

        return scope_users(self.request.user, super().get_queryset())

    def _check_can_manage(self, target):
        if not can_manage_user(self.request.user, target):
            raise PermissionDenied("You cannot manage a user with more privileges than you.")

    def perform_update(self, serializer):
        forbidden = set(serializer.validated_data) - {'username'}
        if forbidden:
            raise PermissionDenied("Only the username can be edited.")
        self._check_can_manage(serializer.instance)
        super().perform_update(serializer)

    def update(self, request, *args, **kwargs):
        if set(request.data) - {'username'}:
            raise PermissionDenied("Only the username can be edited.")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if set(request.data) - {'username'}:
            raise PermissionDenied("Only the username can be edited.")
        return super().partial_update(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        return Response({"error": "New users must verify their email. Use register_with_otp."}, status=405)

    @action(detail=False, methods=['post'])
    def register_with_otp(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_ids = request.data.get('role_ids', [])
        if not isinstance(raw_ids, list) or any(type(value) is not int for value in raw_ids):
            return Response({"role_ids": "Must be a list of role IDs."}, status=400)
        roles = list(Role.objects.filter(id__in=raw_ids, is_active=True))
        if len(roles) != len(set(raw_ids)):
            return Response({"role_ids": "One or more active roles do not exist."}, status=400)
        if any(role.code == Role.SUPER_ADMIN for role in roles):
            raise PermissionDenied("Super Admin accounts are created only by the seed process.")
        if not is_super_admin(request.user):
            missing = role_permission_codes(roles) - get_permission_codes(request.user)
            if missing:
                raise PermissionDenied("You can assign only roles whose permissions you hold.")
            actor_scope = Role.SCOPE_RANK.get(get_data_scope(request.user), 0)
            if any(Role.SCOPE_RANK.get(role.data_scope, 0) > actor_scope for role in roles):
                raise PermissionDenied("You cannot assign a role with a wider data scope than your own.")
        data = serializer.validated_data
        try:
            otp = begin_registration(data['email'], data['username'], data['password'], role_ids=[r.id for r in roles])
            _send_otp_email(data['email'], data['username'], otp, "create your account")
        except RegistrationRejected as exc:
            return _rejected(exc)
        except Exception:
            logger.exception("Managed user registration could not start or send verification email")
            from accounts.pending_registration import delete_pending
            try:
                delete_pending({'email': data['email'].strip().lower(), 'username': data['username'].strip()})
            except Exception:
                logger.exception("Could not clear failed managed registration")
            return Response({"error": "Could not start user registration or send the verification code."}, status=500)
        return Response({"message": "Verification code sent. The user will be created after email verification."})

    def perform_destroy(self, instance):
        self._check_can_manage(instance)
        if is_last_active_super_admin(instance):
            raise PermissionDenied("Cannot delete the last active Super Admin account.")
        super().perform_destroy(instance)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            return Response({"error": "You cannot delete your own logged-in account."}, status=400)
        self._check_can_manage(user)
        if is_last_active_super_admin(user):
            return Response({"error": "Cannot delete the last active Super Admin account."}, status=400)
        return super().destroy(request, *args, **kwargs)

    @extend_schema(request=inline_serializer('AssignRoles', {'role_ids': serializers.ListField(child=serializers.IntegerField())}),
                   responses={200: MessageSerializer})
    @action(detail=True, methods=['post'])
    def assign_roles(self, request, pk=None):
        target = self.get_object()
        role_ids = request.data.get('role_ids', [])
        if not isinstance(role_ids, list) or any(type(value) is not int for value in role_ids):
            return Response({"role_ids": "Must be a list of integer role IDs."}, status=400)
        roles = list(Role.objects.filter(id__in=role_ids))
        if len(roles) != len(set(role_ids)):
            return Response({"role_ids": "One or more role IDs do not exist."}, status=400)

        error = check_role_assignment(request.user, target, roles)
        if error:
            raise PermissionDenied(error)
        if any(role.code == Role.SUPER_ADMIN for role in roles):
            raise PermissionDenied("Super Admin accounts are created only by the seed process.")

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
        if user.is_active and is_last_active_super_admin(user):
            return Response({"error": "Cannot deactivate the last active Super Admin account."}, status=400)
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        if not user.is_active:

            revoke_user_tokens(user)
        log_action(request.user, AuditLog.ACTION_ACTIVATE if user.is_active else AuditLog.ACTION_DEACTIVATE, user)
        return Response({"is_active": user.is_active})
