"""JWT helpers: versioned tokens, revocation and the httpOnly refresh cookie."""

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

TOKEN_VERSION_CLAIM = "tv"


def issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    refresh[TOKEN_VERSION_CLAIM] = user.token_version
    return refresh


def revoke_user_tokens(user):
    """Invalidate every access and refresh token the user currently holds.

    Access tokens die because their `tv` claim no longer matches; refresh
    tokens are also blacklisted so they can't be rotated.
    """
    get_user_model().objects.filter(pk=user.pk).update(token_version=user.token_version + 1)
    user.token_version += 1
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


class VersionedJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user.email_verified:
            raise AuthenticationFailed("Email address has not been verified.", code="email_not_verified")
        if validated_token.get(TOKEN_VERSION_CLAIM) != user.token_version:
            raise AuthenticationFailed("Token has been revoked.", code="token_revoked")
        return user


class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        if not user.email_verified:
            raise AuthenticationFailed("Email address has not been verified.", code="email_not_verified")
        token = super().get_token(user)
        token[TOKEN_VERSION_CLAIM] = user.token_version
        return token


class VersionedTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = RefreshToken(attrs["refresh"])
        user = get_user_model().objects.filter(pk=refresh.get("user_id")).first()
        if user is None or not user.is_active or not user.email_verified:
            raise AuthenticationFailed("No active account found for the given token.", code="no_active_account")
        if refresh.get(TOKEN_VERSION_CLAIM) != user.token_version:
            raise AuthenticationFailed("Token has been revoked.", code="token_revoked")
        return super().validate(attrs)




def set_refresh_cookie(response, refresh_token):
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        str(refresh_token),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=settings.REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response):
    response.delete_cookie(
        settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )


def get_refresh_from_request(request):
    """Refresh token from the httpOnly cookie, falling back to the body for API clients."""
    return request.COOKIES.get(settings.REFRESH_COOKIE_NAME) or request.data.get("refresh")
