from rest_framework import serializers

from .models import Module, Permission, Role


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'name', 'slug', 'route', 'order', 'is_system']
        read_only_fields = ['is_system']


class PermissionSerializer(serializers.ModelSerializer):
    module_name = serializers.CharField(source='module.name', read_only=True)

    class Meta:
        model = Permission
        fields = ['id', 'module', 'module_name', 'action', 'codename']


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    user_count = serializers.IntegerField(source='users.count', read_only=True)

    class Meta:
        model = Role
        fields = ['id', 'name', 'code', 'is_system', 'is_active', 'data_scope', 'permissions', 'user_count']
        # `code` and `is_system` identify built-in roles; they can only be set by seed_data.
        read_only_fields = ['code', 'is_system']
