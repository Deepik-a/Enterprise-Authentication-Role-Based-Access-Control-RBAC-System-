import csv

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from accounts.permissions import HasModulePermission
from accounts.rbac import get_data_scope
from roles.models import Role
from roles.views import crud_map

from .models import Order, Product
from .serializers import OrderSerializer, OrderStatusSerializer, ProductSerializer


def scope_orders(user, queryset):
    """Object-level scoping. Records outside the scope simply don't exist for the caller (404)."""
    scope = get_data_scope(user)
    if scope == Role.SCOPE_ALL:
        return queryset
    if scope == Role.SCOPE_TEAM:
        return queryset.filter(Q(customer=user) | Q(customer__manager=user))
    return queryset.filter(customer=user)


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    permission_map = crud_map('products')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class OrderViewSet(ModelViewSet):
    queryset = Order.objects.select_related('customer', 'product').order_by('id')
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]

    permission_map = {
        'list': 'orders_view',
        'retrieve': 'orders_view',
        'create': 'orders_create',
        'update': 'orders_edit',
        'partial_update': 'orders_edit',
        'cancel': 'orders_cancel',
    }
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_queryset(self):
        return scope_orders(self.request.user, super().get_queryset())

    def get_serializer_class(self):
        if self.action in ('update', 'partial_update'):
            return OrderStatusSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        product = serializer.validated_data['product']
        serializer.save(customer=self.request.user, unit_price=product.price)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status != Order.STATUS_PENDING:
            return Response({"error": "Only pending orders can be cancelled."}, status=400)
        order.status = Order.STATUS_CANCELLED
        order.save(update_fields=['status'])
        return Response(OrderSerializer(order).data)


def _report_rows(user):
    orders = scope_orders(user, Order.objects.all())
    line_total = ExpressionWrapper(F('unit_price') * F('quantity'), output_field=DecimalField(max_digits=12, decimal_places=2))
    return orders.values('status').annotate(orders=Count('id'), revenue=Sum(line_total)).order_by('status')


class ReportSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permission = 'reports_view'

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        rows = list(_report_rows(request.user))
        return Response({
            'scope': get_data_scope(request.user),
            'by_status': rows,
            'total_orders': sum(r['orders'] for r in rows),
            'total_revenue': sum((r['revenue'] or 0) for r in rows),
        })


class ReportExportView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permission = 'reports_export'

    @extend_schema(responses={(200, 'text/csv'): OpenApiTypes.STR})
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders-report.csv"'
        writer = csv.writer(response)
        writer.writerow(['status', 'orders', 'revenue'])
        for row in _report_rows(request.user):
            writer.writerow([row['status'], row['orders'], row['revenue'] or 0])
        return response
