from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

User = get_user_model()


def run_password_validators(password, user):
    """Run Django's AUTH_PASSWORD_VALIDATORS and turn failures into a DRF error."""
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages))
    return password


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "username", "password"]

    def validate(self, attrs):

        candidate = User(email=attrs.get("email"), username=attrs.get("username"))
        try:
            run_password_validators(attrs.get("password"), candidate)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"password": exc.detail})
        return attrs

    def create(self, validated_data):

        return User.objects.create_user(**validated_data, is_active=False, email_verified=False)


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.StringRelatedField(many=True, read_only=True)
    role_ids = serializers.PrimaryKeyRelatedField(many=True, read_only=True, source='roles')
    manager = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    manager_email = serializers.EmailField(source='manager.email', read_only=True, default=None)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'is_active', 'email_verified',
                  'roles', 'role_ids', 'manager', 'manager_email',
                  'date_joined', 'last_login']

        read_only_fields = ['id', 'date_joined', 'last_login', 'is_active', 'email_verified']

    def validate_manager(self, manager):
        if manager is not None and self.instance is not None and manager.pk == self.instance.pk:
            raise serializers.ValidationError("A user cannot be their own manager.")
        return manager

    def validate(self, attrs):
        return attrs
