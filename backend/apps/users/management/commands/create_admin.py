from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create an admin user with no organization."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)

    def handle(self, *args, **options):
        email = options["email"]
        if User.objects.filter(email=email, organization__isnull=True).exists():
            self.stderr.write(f"User with email '{email}' already exists.")
            return

        user = User.objects.create_user(
            email=email,
            username=options["username"],
            password=options["password"],
            role=User.ROLE_ADMIN,
            organization=None,
            is_staff=True,
        )
        self.stdout.write(self.style.SUCCESS(f"Admin user '{user.email}' created successfully."))
