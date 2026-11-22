from django.contrib import admin

from .models import Module, Permission, Role

admin.site.register(Module)
admin.site.register(Permission)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_system', 'is_active', 'data_scope')
    filter_horizontal = ('permissions',)
