from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from roles.models import Role

from .models import OneTimeToken, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('RBAC', {'fields': ('roles', 'manager', 'email_verified', 'token_version')}),
    )
    list_display = ('email', 'username', 'is_active', 'email_verified', 'is_superuser')
    filter_horizontal = ('roles', 'groups', 'user_permissions')
    actions = None

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        protected = {'is_superuser', 'is_staff', 'groups', 'user_permissions'}
        filtered = []
        for name, options in fieldsets:
            fields = options.get('fields', ())
            if isinstance(fields, str):
                fields = (fields,)
            fields = tuple(field for field in fields if field not in protected)
            if fields:
                filtered.append((name, {**options, 'fields': fields}))
        return filtered

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.roles.filter(code=Role.SUPER_ADMIN).exists():
            readonly.extend(['roles', 'is_active'])
        return readonly

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'roles':
            kwargs['queryset'] = Role.objects.exclude(code=Role.SUPER_ADMIN)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.roles.filter(code=Role.SUPER_ADMIN).exists():
            return False
        return super().has_delete_permission(request, obj)


@admin.register(OneTimeToken)
class OneTimeTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'purpose', 'created_at', 'expires_at', 'used_at')
    readonly_fields = ('token_hash',)
