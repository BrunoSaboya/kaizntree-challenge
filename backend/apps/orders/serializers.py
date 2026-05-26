from rest_framework import serializers

from .models import PurchaseOrder, SalesOrder


class PurchaseOrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    total_cost = serializers.DecimalField(max_digits=12, decimal_places=4, read_only=True)
    stock_identifier = serializers.CharField(source="stock.identifier", read_only=True, default=None)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "product", "product_name", "product_sku",
            "stock", "stock_identifier",
            "quantity", "cost_per_unit", "total_cost",
            "status", "notes", "order_date", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "stock", "stock_identifier", "product_name", "product_sku", "total_cost", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context["request"]
        product = attrs.get("product") or (self.instance.product if self.instance else None)
        if product and product.owner != request.user:
            raise serializers.ValidationError({"product": "Product not found."})
        return attrs

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def validate_cost_per_unit(self, value):
        if value <= 0:
            raise serializers.ValidationError("Cost per unit must be greater than zero.")
        return value


class ConfirmPurchaseOrderSerializer(serializers.Serializer):
    stock_identifier = serializers.CharField(max_length=100)


class SalesOrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    stock_identifier = serializers.CharField(source="stock.identifier", read_only=True, default=None)
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=4, read_only=True)

    class Meta:
        model = SalesOrder
        fields = [
            "id", "product", "product_name", "product_sku",
            "stock", "stock_identifier",
            "quantity", "price_per_unit", "total_revenue",
            "status", "notes", "order_date", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "product_name", "product_sku", "stock_identifier", "total_revenue", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context["request"]
        product = attrs.get("product") or (self.instance.product if self.instance else None)
        if product and product.owner != request.user:
            raise serializers.ValidationError({"product": "Product not found."})

        stock = attrs.get("stock") or (self.instance.stock if self.instance else None)
        if stock and stock.owner != request.user:
            raise serializers.ValidationError({"stock": "Stock not found."})

        if stock and product and stock.product != product:
            raise serializers.ValidationError({"stock": "Stock does not belong to this product."})

        return attrs

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def validate_price_per_unit(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price per unit must be greater than zero.")
        return value
