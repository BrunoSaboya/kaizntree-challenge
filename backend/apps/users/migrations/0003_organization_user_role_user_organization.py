from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_orgs(apps, schema_editor):
    User = apps.get_model("users", "User")
    Organization = apps.get_model("users", "Organization")
    db_alias = schema_editor.connection.alias

    # Every existing user gets their own org to preserve existing data.
    # Fresh admin users should be created via the create_admin management command.
    for user in User.objects.using(db_alias).all():
        org = Organization.objects.using(db_alias).create(
            name=f"{user.username}'s Organization",
        )
        org.owner = user
        org.save()
        user.organization = org
        user.role = "owner"
        user.save()


def reverse_backfill_orgs(apps, schema_editor):
    Organization = apps.get_model("users", "Organization")
    db_alias = schema_editor.connection.alias
    Organization.objects.using(db_alias).all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_user_options_alter_user_email_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'organizations',
            },
        ),
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[('admin', 'Admin'), ('owner', 'Owner'), ('member', 'Member')],
                default='owner',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='members',
                to='users.organization',
            ),
        ),
        migrations.AddField(
            model_name='organization',
            name='owner',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='owned_organizations',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(backfill_orgs, reverse_code=reverse_backfill_orgs),
    ]
