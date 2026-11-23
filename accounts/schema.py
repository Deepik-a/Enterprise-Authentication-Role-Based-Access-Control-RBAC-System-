"""Tell drf-spectacular that our JWT auth class is a normal Bearer scheme."""
from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme


class VersionedJWTScheme(SimpleJWTScheme):
    target_class = 'accounts.tokens.VersionedJWTAuthentication'
    name = 'jwtAuth'
