from django.db import migrations, models
import django.db.models.deletion


def backfill_organization(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    for model_name in ("PurchaseOrder", "SalesOrder"):
        Model = apps.get_model("orders", model_name)
        objs = list(Model.objects.using(db_alias).select_related("owner__organization").all())
        for obj in objs:
            obj.organization = obj.owner.organization
        Model.objects.using(db_alias).bulk_update(objs, ["organization"])


def reverse_backfill_organization(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    for model_name in ("PurchaseOrder", "SalesOrder"):
        Model = apps.get_model("orders", model_name)
        objs = list(Model.objects.using(db_alias).select_related("organization__owner").all())
        for obj in objs:
            obj.owner = obj.organization.owner
        Model.objects.using(db_alias).bulk_update(objs, ["owner"])


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_purchaseorder_supplier'),
        ('users', '0003_organization_user_role_user_organization'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseorder',
            name='organization',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='purchase_orders',
                to='users.organization',
            ),
        ),
        migrations.AddField(
            model_name='salesorder',
            name='organization',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='sales_orders',
                to='users.organization',
            ),
        ),
        migrations.RunPython(backfill_organization, reverse_code=reverse_backfill_organization),
        migrations.AlterField(
            model_name='purchaseorder',
            name='organization',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='purchase_orders',
                to='users.organization',
            ),
        ),
        migrations.AlterField(
            model_name='salesorder',
            name='organization',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='sales_orders',
                to='users.organization',
            ),
        ),
        migrations.RemoveField(model_name='purchaseorder', name='owner'),
        migrations.RemoveField(model_name='salesorder', name='owner'),
    ]
