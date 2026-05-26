from django.contrib import admin

from .models import Product, Stock


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "sku", "unit_type", "owner", "created_at"]
    list_filter = ["unit_type"]
    search_fields = ["name", "sku"]


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ["product", "identifier", "quantity", "owner", "created_at"]
    search_fields = ["identifier", "product__name"]
