from accounts.permissions import HasModulePermission
from accounts.serializers import RegisterSerializer
from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response  import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.viewsets import ModelViewSet  #automatically provides CRUD operations for users: list, create, retrieve, update, and delete.
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

class RegisterView(APIView):
    permission_classes=[AllowAny] #anyone can register

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User created"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]  #only authenticated user can access the endpoint
    
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist() #It adds the refresh token to the blacklist so it cannot be used again to refresh an access token
            return Response({"message": "Logged out"}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)


#flow is frontend(data)----->urls.py(routes incoming request)---->regsiterview(receives request)----->RegisterSerializer(validates data)------->serializse.save()(calls create())------>Django ORM  create user in postegresql-----sucess message


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()  #specify which users to work with
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['email', 'username']

      @action(detail=True, methods=['post'])  #creates custom API endpoints:
    def assign_roles(self, request, pk=None): #assigns roles to a user,
        user = self.get_object()
        role_ids = request.data.get('role_ids', [])
        user.roles.set(role_ids)
        return Response({"message": "Roles assigned"})
    
    @action(detail=True, methods=['post'])  #activates or deactivates a user.
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        return Response({"is_active": user.is_active})

        # Example: protecting user management
    permission_classes = [IsAuthenticated, HasModulePermission]
    
    def get_required_permission(self):
        """Map ViewSet actions to permission codenames"""
        action_map = {
            'list': 'user_management_view',
            'retrieve': 'user_management_view',
            'create': 'user_management_create',
            'update': 'user_management_edit',
            'partial_update': 'user_management_edit',
            'destroy': 'user_management_delete',
        }
        return action_map.get(self.action)
    
    # Override to set required_permission dynamically
    def initial(self, request, *args, **kwargs):
        self.required_permission = self.get_required_permission()
        super().initial(request, *args, **kwargs)


class MeView(APIView):
    """GET /api/auth/me/ — returns current user + their roles + their permissions"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        permissions = Permission.objects.filter(
            roles__users=user, roles__is_active=True
        ).values_list('codename', flat=True).distinct()
        
        modules = Module.objects.filter(
            permissions__roles__users=user, permissions__roles__is_active=True
        ).distinct().values('id', 'name')
        
        return Response({
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "roles": list(user.roles.values_list('name', flat=True)),
            "permissions": list(permissions),
            "modules": list(modules),
        })