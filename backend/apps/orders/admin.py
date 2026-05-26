from django.contrib import admin

from .models import PurchaseOrder, SalesOrder


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "quantity", "cost_per_unit", "status", "order_date"]
    list_filter = ["status"]


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "quantity", "price_per_unit", "status", "order_date"]
    list_filter = ["status"]
