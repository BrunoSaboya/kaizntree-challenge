from django.db import models


class UnitType(models.TextChoices):
    KG = "kg", "Kilograms"
    G = "g", "Grams"
    L = "l", "Litres"
    ML = "ml", "Millilitres"
    COUNT = "count", "Unit"


class Product(models.Model):
    organization = models.ForeignKey(
        "users.Organization",
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    sku = models.CharField(max_length=100)
    unit_type = models.CharField(max_length=10, choices=UnitType.choices, default=UnitType.COUNT)
    min_stock_quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        unique_together = [("organization", "sku")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.sku})"


class Stock(models.Model):
    organization = models.ForeignKey(
        "users.Organization",
        on_delete=models.CASCADE,
        related_name="stock_entries",
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_entries")
    identifier = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    notes = models.TextField(blank=True, default="")
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stock"
        unique_together = [("organization", "product", "identifier")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} — {self.identifier} ({self.quantity})"


class MovementType(models.TextChoices):
    PURCHASE_CONFIRMED = "purchase_confirmed", "Purchase Order Confirmed"
    SALES_CONFIRMED = "sales_confirmed", "Sales Order Confirmed"
    SALES_CANCELLED = "sales_cancelled", "Sales Order Cancelled"
    MANUAL_ADJUSTMENT = "manual_adjustment", "Manual Adjustment"


class StockMovement(models.Model):
    organization = models.ForeignKey(
        "users.Organization",
        on_delete=models.CASCADE,
        related_name="stock_movements",
    )
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="movements")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=30, choices=MovementType.choices)
    quantity_change = models.DecimalField(max_digits=12, decimal_places=3)
    reference_type = models.CharField(max_length=50, blank=True, default="")
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stock_movements"
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.quantity_change >= 0 else ""
        return f"{self.movement_type} {sign}{self.quantity_change} — {self.stock.identifier}"
