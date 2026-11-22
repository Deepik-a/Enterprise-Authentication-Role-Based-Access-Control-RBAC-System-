from rest_framework import serializers

from .models import Order, Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'is_active', 'created_by', 'created_at']
        read_only_fields = ['created_by', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True))

    class Meta:
        model = Order
        fields = ['id', 'customer', 'customer_email', 'product', 'product_name', 'quantity',
                  'unit_price', 'total', 'status', 'created_at']
        # customer and price come from the server, not the client.
        read_only_fields = ['customer', 'unit_price', 'status', 'created_at']


class OrderStatusSerializer(serializers.ModelSerializer):
    """Used by staff with orders_edit. Only the status can change."""

    class Meta:
        model = Order
        fields = ['status']
