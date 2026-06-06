from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Organization, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "username", "role", "organization", "is_staff", "date_joined"]
    list_filter = ["role", "is_staff"]
    ordering = ["-date_joined"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Role & Org", {"fields": ("role", "organization")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Role & Org", {"fields": ("role", "organization")}),
    )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "created_at"]
    search_fields = ["name"]
