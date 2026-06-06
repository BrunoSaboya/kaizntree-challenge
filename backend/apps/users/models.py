from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_organizations",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations"

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_ADMIN = "admin"
    ROLE_OWNER = "owner"
    ROLE_MEMBER = "member"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_OWNER, "Owner"),
        (ROLE_MEMBER, "Member"),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_OWNER)
    organization = models.ForeignKey(
        "users.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email
