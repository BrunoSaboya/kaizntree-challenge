from rest_framework import serializers

from .models import Product, Stock, StockMovement


class ProductSerializer(serializers.ModelSerializer):
    total_stock = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True, default=0)

    class Meta:
        model = Product
        fields = [
            "id", "name", "description", "sku", "unit_type",
            "min_stock_quantity", "total_stock", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "total_stock", "created_at", "updated_at"]

    def validate_sku(self, value):
        value = value.upper().strip()
        request = self.context.get("request")
        if request and request.user:
            qs = Product.objects.filter(organization=request.user.organization, sku=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("A product with this SKU already exists.")
        return value


class StockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = Stock
        fields = [
            "id", "product", "product_name", "product_sku",
            "identifier", "quantity", "notes", "expiry_date", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "product_name", "product_sku", "created_at", "updated_at"]

    def validate_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        product = attrs.get("product") or (self.instance.product if self.instance else None)
        if product and product.organization_id != request.user.organization_id:
            raise serializers.ValidationError({"product": "Product not found."})
        return attrs


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = [
            "id", "movement_type", "quantity_change",
            "reference_type", "reference_id", "notes", "created_at",
        ]
        read_only_fields = fields
