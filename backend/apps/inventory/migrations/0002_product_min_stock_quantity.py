from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="min_stock_quantity",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
