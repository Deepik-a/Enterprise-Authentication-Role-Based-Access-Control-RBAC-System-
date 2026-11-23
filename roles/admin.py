from django.contrib import admin

from .models import Module, Permission, Role

admin.site.register(Module)
admin.site.register(Permission)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_system', 'is_active', 'data_scope')
    filter_horizontal = ('permissions',)
    actions = None

    def get_readonly_fields(self, request, obj=None):
        readonly = ['code', 'is_system']
        if obj and obj.code == Role.SUPER_ADMIN:
            readonly.extend(['name', 'permissions', 'is_active', 'data_scope'])
        return readonly

    def has_delete_permission(self, request, obj=None):
        if obj and obj.code == Role.SUPER_ADMIN:
            return False
        return super().has_delete_permission(request, obj)
