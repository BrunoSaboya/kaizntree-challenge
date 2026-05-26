import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("sku", models.CharField(max_length=100)),
                (
                    "unit_type",
                    models.CharField(
                        choices=[
                            ("kg", "Kilograms"),
                            ("g", "Grams"),
                            ("l", "Litres"),
                            ("ml", "Millilitres"),
                            ("count", "Count"),
                        ],
                        default="count",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="products",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "products",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Stock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("identifier", models.CharField(max_length=100)),
                ("quantity", models.DecimalField(decimal_places=3, default=0, max_digits=12)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stock_entries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stock_entries",
                        to="inventory.product",
                    ),
                ),
            ],
            options={
                "db_table": "stock",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="product",
            unique_together={("owner", "sku")},
        ),
        migrations.AlterUniqueTogether(
            name="stock",
            unique_together={("owner", "product", "identifier")},
        ),
    ]
