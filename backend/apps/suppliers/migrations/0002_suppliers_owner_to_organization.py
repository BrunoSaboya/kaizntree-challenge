from django.db import migrations, models
import django.db.models.deletion


def backfill_organization(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    Supplier = apps.get_model("suppliers", "Supplier")
    objs = list(Supplier.objects.using(db_alias).select_related("owner__organization").all())
    for obj in objs:
        obj.organization = obj.owner.organization
    Supplier.objects.using(db_alias).bulk_update(objs, ["organization"])


def reverse_backfill_organization(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    Supplier = apps.get_model("suppliers", "Supplier")
    objs = list(Supplier.objects.using(db_alias).select_related("organization__owner").all())
    for obj in objs:
        obj.owner = obj.organization.owner
    Supplier.objects.using(db_alias).bulk_update(objs, ["owner"])


class Migration(migrations.Migration):

    dependencies = [
        ('suppliers', '0001_initial'),
        ('users', '0003_organization_user_role_user_organization'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplier',
            name='organization',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='suppliers',
                to='users.organization',
            ),
        ),
        migrations.RunPython(backfill_organization, reverse_code=reverse_backfill_organization),
        migrations.AlterField(
            model_name='supplier',
            name='organization',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='suppliers',
                to='users.organization',
            ),
        ),
        migrations.RemoveField(model_name='supplier', name='owner'),
    ]
