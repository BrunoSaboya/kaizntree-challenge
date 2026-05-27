from django.conf import settings
from django.db import models


class UnitType(models.TextChoices):
    KG = "kg", "Kilograms"
    G = "g", "Grams"
    L = "l", "Litres"
    ML = "ml", "Millilitres"
    COUNT = "count", "Count"


class Product(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
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
        unique_together = [("owner", "sku")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.sku})"


class Stock(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stock_entries",
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_entries")
    identifier = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stock"
        unique_together = [("owner", "product", "identifier")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} — {self.identifier} ({self.quantity})"
