from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import OneTimeToken, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('RBAC', {'fields': ('roles', 'manager', 'email_verified', 'token_version')}),
    )
    list_display = ('email', 'username', 'is_active', 'email_verified', 'is_superuser')
    filter_horizontal = ('roles', 'groups', 'user_permissions')


@admin.register(OneTimeToken)
class OneTimeTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'purpose', 'created_at', 'expires_at', 'used_at')
    readonly_fields = ('token_hash',)
