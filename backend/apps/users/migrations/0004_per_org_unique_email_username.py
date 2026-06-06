from django.db import migrations, models
import django.contrib.auth.validators


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_organization_user_role_user_organization'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(
                help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.',
                max_length=150,
                validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
            ),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(
                condition=models.Q(organization__isnull=False),
                fields=['email', 'organization'],
                name='unique_email_per_org',
            ),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(
                condition=models.Q(organization__isnull=False),
                fields=['username', 'organization'],
                name='unique_username_per_org',
            ),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(
                condition=models.Q(organization__isnull=True),
                fields=['email'],
                name='unique_email_no_org',
            ),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(
                condition=models.Q(organization__isnull=True),
                fields=['username'],
                name='unique_username_no_org',
            ),
        ),
    ]
