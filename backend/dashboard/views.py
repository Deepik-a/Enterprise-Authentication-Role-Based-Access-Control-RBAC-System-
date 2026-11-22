from django.contrib.auth import get_user_model
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.rbac import get_permission_codes
from accounts.views import scope_users
from roles.models import Module, Role
from shop.models import Order, Product
from shop.views import scope_orders

User = get_user_model()


class DashboardStatsView(APIView):
    """Counts for the dashboard.

    Every logged-in user may call it, but each number is only included when
    the caller may view that kind of record, and record counts respect the
    caller's data scope (a Customer sees only their own order count).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        user = request.user
        perms = get_permission_codes(user)
        data = {}
        if 'user_management_view' in perms:
            data['users'] = scope_users(user, User.objects.all()).count()
        if 'role_management_view' in perms:
            data['roles'] = Role.objects.count()
        if 'module_management_view' in perms:
            data['modules'] = Module.objects.count()
        if 'products_view' in perms:
            data['products'] = Product.objects.filter(is_active=True).count()
        if 'orders_view' in perms:
            data['orders'] = scope_orders(user, Order.objects.all()).count()
        return Response(data)
