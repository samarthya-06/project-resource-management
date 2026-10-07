from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class AccountManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("must_change_password", False)
        if extra_fields["role"] != User.Role.ADMIN:
            raise ValueError("A superuser must have the Admin role.")
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        PROJECT_MANAGER = "PROJECT_MANAGER", "Project Manager"
        EMPLOYEE = "EMPLOYEE", "Employee"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    must_change_password = models.BooleanField(default=True)
    objects = AccountManager()

    class Meta(AbstractUser.Meta):
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=["ADMIN", "PROJECT_MANAGER", "EMPLOYEE"]),
                name="account_valid_role",
            ),
            models.CheckConstraint(
                condition=models.Q(is_staff=False, is_superuser=False) | models.Q(role="ADMIN"),
                name="account_admin_privileges_require_admin_role",
            ),
        ]
