from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User


class Command(BaseCommand):
    help = "Create deterministic development accounts; preserve existing accounts and passwords."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo is only available with DJANGO_DEBUG=True.")
        password = settings.DEMO_PASSWORD
        if not password or password.startswith("replace-with-"):
            raise CommandError("Set a strong DEMO_PASSWORD in your local environment first.")
        accounts = [
            ("admin@demo.local", "Samarthya", "Jambavalikar", User.Role.ADMIN, True),
            ("neha@demo.local", "Neha", "Sharma", User.Role.PROJECT_MANAGER, True),
            ("arjun@demo.local", "Arjun", "Patil", User.Role.PROJECT_MANAGER, True),
            ("asha@demo.local", "Asha", "Deshmukh", User.Role.EMPLOYEE, True),
            ("ravi@demo.local", "Ravi", "Kulkarni", User.Role.EMPLOYEE, True),
            ("meera@demo.local", "Meera", "Shah", User.Role.EMPLOYEE, False),
            ("dev@demo.local", "Dev", "Rao", User.Role.EMPLOYEE, True),
        ]
        with transaction.atomic():
            for username, first_name, last_name, role, active in accounts:
                if User.objects.filter(username=username).exists():
                    self.stdout.write(f"Preserved {username}")
                    continue
                user = User(
                    username=username,
                    email=username,
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    is_active=active,
                    must_change_password=False,
                )
                try:
                    validate_password(password, user)
                except ValidationError as exc:
                    raise CommandError("DEMO_PASSWORD: " + "; ".join(exc.messages)) from exc
                if role == User.Role.ADMIN:
                    user.is_staff = user.is_superuser = True
                user.set_password(password)
                user.full_clean()
                user.save()
                self.stdout.write(f"Created {username} ({user.get_role_display()})")
        self.stdout.write(
            self.style.SUCCESS("Demo accounts ready. Password is DEMO_PASSWORD; never printed.")
        )
