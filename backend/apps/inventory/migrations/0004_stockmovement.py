from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0003_stock_expiry_date"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StockMovement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("movement_type", models.CharField(
                    choices=[
                        ("purchase_confirmed", "Purchase Order Confirmed"),
                        ("sales_confirmed", "Sales Order Confirmed"),
                        ("sales_cancelled", "Sales Order Cancelled"),
                        ("manual_adjustment", "Manual Adjustment"),
                    ],
                    max_length=30,
                )),
                ("quantity_change", models.DecimalField(decimal_places=3, max_digits=12)),
                ("reference_type", models.CharField(blank=True, default="", max_length=50)),
                ("reference_id", models.PositiveIntegerField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stock_movements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="movements",
                        to="inventory.product",
                    ),
                ),
                (
                    "stock",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="movements",
                        to="inventory.stock",
                    ),
                ),
            ],
            options={
                "db_table": "stock_movements",
                "ordering": ["-created_at"],
            },
        ),
    ]
