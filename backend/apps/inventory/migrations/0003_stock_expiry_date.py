from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0002_product_min_stock_quantity"),
    ]

    operations = [
        migrations.AddField(
            model_name="stock",
            name="expiry_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
