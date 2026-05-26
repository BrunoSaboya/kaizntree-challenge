from django.conf import settings
from django.db import models


class OrderStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    CONFIRMED = "confirmed", "Confirmed"
    CANCELLED = "cancelled", "Cancelled"


class PurchaseOrder(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="purchase_orders",
    )
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )
    stock = models.ForeignKey(
        "inventory.Stock",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_orders",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    cost_per_unit = models.DecimalField(max_digits=12, decimal_places=4)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.DRAFT)
    notes = models.TextField(blank=True, default="")
    order_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "purchase_orders"
        ordering = ["-order_date", "-created_at"]

    @property
    def total_cost(self):
        return self.quantity * self.cost_per_unit

    def __str__(self):
        return f"PO #{self.pk} — {self.product.name} ({self.status})"


class SalesOrder(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sales_orders",
    )
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.PROTECT,
        related_name="sales_orders",
    )
    stock = models.ForeignKey(
        "inventory.Stock",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sales_orders",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=4)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.DRAFT)
    notes = models.TextField(blank=True, default="")
    order_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sales_orders"
        ordering = ["-order_date", "-created_at"]

    @property
    def total_revenue(self):
        return self.quantity * self.price_per_unit

    def __str__(self):
        return f"SO #{self.pk} — {self.product.name} ({self.status})"
