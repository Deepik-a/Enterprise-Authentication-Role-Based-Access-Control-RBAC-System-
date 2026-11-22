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
        # Build an unsaved user so UserAttributeSimilarityValidator can compare against email/username.
        candidate = User(email=attrs.get("email"), username=attrs.get("username"))
        try:
            run_password_validators(attrs.get("password"), candidate)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"password": exc.detail})
        return attrs

    def create(self, validated_data):
        # Self-registered accounts stay inactive until the email link is clicked.
        return User.objects.create_user(**validated_data, is_active=False, email_verified=False)


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.StringRelatedField(many=True, read_only=True)
    role_ids = serializers.PrimaryKeyRelatedField(many=True, read_only=True, source='roles')
    password = serializers.CharField(write_only=True, required=False)
    manager = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    manager_email = serializers.EmailField(source='manager.email', read_only=True, default=None)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'is_active', 'email_verified',
                  'is_superuser', 'roles', 'role_ids', 'manager', 'manager_email', 'password',
                  'date_joined', 'last_login']
        # is_active only changes through toggle_active, which has its own guards.
        read_only_fields = ['id', 'date_joined', 'last_login', 'is_superuser', 'is_active', 'email_verified']

    def validate_manager(self, manager):
        if manager is not None and self.instance is not None and manager.pk == self.instance.pk:
            raise serializers.ValidationError("A user cannot be their own manager.")
        return manager

    def validate(self, attrs):
        password = attrs.get('password')
        if password is not None:
            user = self.instance or User(email=attrs.get('email'), username=attrs.get('username'))
            try:
                run_password_validators(password, user)
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({'password': exc.detail})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        # Admin-created accounts are trusted; no email activation step.
        user.email_verified = True
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        # Never let the raw password reach the model field.
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            from accounts.tokens import revoke_user_tokens

            instance.set_password(password)
            instance.save(update_fields=['password'])
            revoke_user_tokens(instance)
        return instance
