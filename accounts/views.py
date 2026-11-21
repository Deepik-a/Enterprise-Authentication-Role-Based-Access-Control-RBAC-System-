import uuid
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from accounts.permissions import HasModulePermission
from accounts.serializers import RegisterSerializer, UserSerializer
from roles.models import Permission, Module

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User created"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logged out"}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(ModelViewSet):
    queryset = User.objects.all().order_by('-id')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['email', 'username', 'first_name', 'last_name']
    filterset_fields = ['is_active', 'roles']

    def get_required_permission(self):
        action_map = {
            'list': 'user_management_view',
            'retrieve': 'user_management_view',
            'create': 'user_management_create',
            'update': 'user_management_edit',
            'partial_update': 'user_management_edit',
            'destroy': 'user_management_delete',
        }
        return action_map.get(self.action)

    def initial(self, request, *args, **kwargs):
        self.required_permission = self.get_required_permission()
        super().initial(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            return Response({"error": "You cannot delete your own logged-in account."}, status=400)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def assign_roles(self, request, pk=None):
        user = self.get_object()
        role_ids = request.data.get('role_ids', [])
        user.roles.set(role_ids)
        return Response({"message": "Roles assigned"})

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        if user == request.user and user.is_active:
            return Response({"error": "You cannot deactivate your own account."}, status=400)
        if user.is_superuser and user.is_active and User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
            return Response({"error": "Cannot deactivate the only active superuser account."}, status=400)
        user.is_active = not user.is_active
        user.save()
        return Response({"is_active": user.is_active})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        if user.is_superuser:
            permissions = list(Permission.objects.all().values_list('codename', flat=True).distinct())
            modules = list(Module.objects.all().values('id', 'name'))
            roles = list(user.roles.values_list('name', flat=True))
            if "Super Admin" not in roles:
                roles.append("Super Admin")
        else:
            permissions = list(Permission.objects.filter(
                roles__users=user, roles__is_active=True
            ).values_list('codename', flat=True).distinct())

            modules = list(Module.objects.filter(
                permissions__roles__users=user, permissions__roles__is_active=True
            ).distinct().values('id', 'name'))
            roles = list(user.roles.values_list('name', flat=True))

        return Response({
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_superuser": user.is_superuser,
            "roles": roles,
            "permissions": permissions,
            "modules": modules,
        })


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            token = str(uuid.uuid4())
            cache.set(f'reset_{token}', user.id, timeout=3600)
            return Response({"reset_token": token, "message": "Use this token to reset password"})
        except User.DoesNotExist:
            return Response({"message": "If email exists, reset link sent"})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        user_id = cache.get(f'reset_{token}')
        if not user_id:
            return Response({"error": "Invalid or expired token"}, status=400)
        user = User.objects.get(id=user_id)
        user.set_password(new_password)
        user.save()
        cache.delete(f'reset_{token}')
        return Response({"message": "Password reset successful"})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        if not request.user.check_password(old_password):
            return Response({"error": "Wrong current password"}, status=400)
        request.user.set_password(new_password)
        request.user.save()
        return Response({"message": "Password changed"})
