
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Role, Permission, Module
from .serializers import RoleSerializer, PermissionSerializer, ModuleSerializer


# Handles all CRUD operations related to Roles.
class RoleViewSet(ModelViewSet):

    # Specifies which Role records should be accessed from the database.
    queryset = Role.objects.all()

    # Specifies how Role data should be converted to and from JSON.
    serializer_class = RoleSerializer

    # Only logged-in users can access these APIs.
    permission_classes = [IsAuthenticated]

    # Creates a custom POST endpoint:
    # POST /api/roles/1/assign_permissions/
    @action(detail=True, methods=['post'])
    def assign_permissions(self, request, pk=None):

        # Fetches the specific role using its primary key (ID).
        role = self.get_object()

        # Gets permission IDs from the request body.
        # Example: {"permission_ids": [1, 2]}
        permission_ids = request.data.get('permission_ids', [])

        # Assigns the selected permissions to this role.
        # set() replaces the existing permissions with the new ones.
        role.permissions.set(permission_ids)

        # Sends a success response to the client.
        return Response({"message": "Permissions assigned"})


# Handles CRUD operations related to Permissions.
class PermissionViewSet(ModelViewSet):

    # Fetches all Permission records from the database.
    queryset = Permission.objects.all()

    # Converts Permission model data into JSON and validates input.
    serializer_class = PermissionSerializer

    # Only authenticated users can access these APIs.
    permission_classes = [IsAuthenticated]


# Handles CRUD operations related to Modules.
class ModuleViewSet(ModelViewSet):

    # Fetches all Module records from the database.
    queryset = Module.objects.all()

    # Converts Module model data into JSON and validates input.
    serializer_class = ModuleSerializer

    # Only authenticated users can access these APIs.
    permission_classes = [IsAuthenticated]