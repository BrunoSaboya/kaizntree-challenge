from django.contrib import admin

from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "phone", "lead_time_days", "payment_terms", "active", "organization"]
    list_filter = ["active"]
    search_fields = ["name", "email"]
