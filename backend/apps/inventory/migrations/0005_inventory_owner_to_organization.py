from django.db import migrations, models
import django.db.models.deletion


def backfill_organization(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    for model_name in ("Product", "Stock", "StockMovement"):
        Model = apps.get_model("inventory", model_name)
        objs = list(Model.objects.using(db_alias).select_related("owner__organization").all())
        for obj in objs:
            obj.organization = obj.owner.organization
        Model.objects.using(db_alias).bulk_update(objs, ["organization"])


def reverse_backfill_organization(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    for model_name in ("Product", "Stock", "StockMovement"):
        Model = apps.get_model("inventory", model_name)
        objs = list(Model.objects.using(db_alias).select_related("organization__owner").all())
        for obj in objs:
            obj.owner = obj.organization.owner
        Model.objects.using(db_alias).bulk_update(objs, ["owner"])


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_stockmovement'),
        ('users', '0003_organization_user_role_user_organization'),
    ]

    operations = [
        # --- Product ---
        migrations.AddField(
            model_name='product',
            name='organization',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='products',
                to='users.organization',
            ),
        ),
        # --- Stock ---
        migrations.AddField(
            model_name='stock',
            name='organization',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='stock_entries',
                to='users.organization',
            ),
        ),
        # --- StockMovement ---
        migrations.AddField(
            model_name='stockmovement',
            name='organization',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='stock_movements',
                to='users.organization',
            ),
        ),
        # Backfill organization from owner.organization
        migrations.RunPython(backfill_organization, reverse_code=reverse_backfill_organization),
        # Make non-null after backfill
        migrations.AlterField(
            model_name='product',
            name='organization',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='products',
                to='users.organization',
            ),
        ),
        migrations.AlterField(
            model_name='stock',
            name='organization',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='stock_entries',
                to='users.organization',
            ),
        ),
        migrations.AlterField(
            model_name='stockmovement',
            name='organization',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='stock_movements',
                to='users.organization',
            ),
        ),
        # Update unique_together: replace owner with organization
        migrations.AlterUniqueTogether(
            name='product',
            unique_together={('organization', 'sku')},
        ),
        migrations.AlterUniqueTogether(
            name='stock',
            unique_together={('organization', 'product', 'identifier')},
        ),
        # Remove old owner fields
        migrations.RemoveField(model_name='product', name='owner'),
        migrations.RemoveField(model_name='stock', name='owner'),
        migrations.RemoveField(model_name='stockmovement', name='owner'),
    ]
