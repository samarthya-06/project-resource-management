"""Authorized application account operations."""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from accounts.models import User


def require_actor(actor):
    if not getattr(actor, "is_authenticated", False) or not actor.pk:
        raise PermissionDenied("Sign in with an active account.")
    current = User.objects.filter(pk=actor.pk, is_active=True).first()
    if current is None or current.must_change_password:
        raise PermissionDenied("An active account with a changed initial password is required.")
    return current


def lock_actor(actor, *related_ids):
    require_actor(actor)
    list(User.objects.select_for_update().filter(pk__in=[actor.pk, *related_ids]).order_by("pk"))
    return require_actor(actor)


def check_fields(data, allowed):
    unknown = set(data) - set(allowed)
    if unknown:
        raise ValidationError({name: "This field cannot be changed here." for name in unknown})


def require_admin(actor):
    if actor.role != User.Role.ADMIN:
        raise PermissionDenied("Only Admin can manage accounts.")


def validate_role_change(user, role):
    if role == user.role:
        return
    if user.managed_projects.exists():
        raise ValidationError({"role": "Reassign owned projects before changing this role."})
    if user.assigned_tasks.exclude(status="COMPLETED").exists():
        raise ValidationError({"role": "Reassign unfinished tasks before changing this role."})
    if user.project_memberships.exists():
        raise ValidationError({"role": "Remove project memberships before changing this role."})


def _password(user, password):
    if not isinstance(password, str) or not password:
        raise ValidationError({"password": "Enter an initial password."})
    validate_password(password, user)
    user.set_password(password)
    user.must_change_password = True


@transaction.atomic
def create_account(actor, **data):
    require_admin(lock_actor(actor))
    check_fields(data, {"username", "email", "first_name", "last_name", "role", "password"})
    password = data.pop("password", None)
    user = User(**data)
    _password(user, password)
    user.full_clean()
    user.save()
    return user


@transaction.atomic
def update_account(actor, user_id, **data):
    require_admin(lock_actor(actor, user_id))
    check_fields(data, {"username", "email", "first_name", "last_name", "role", "password"})
    user = User.objects.get(pk=user_id)
    validate_role_change(user, data.get("role", user.role))
    for field, value in data.items():
        if field != "password":
            setattr(user, field, value)
    if "password" in data:
        _password(user, data["password"])
    user.full_clean()
    user.save()
    return user


@transaction.atomic
def deactivate_account(actor, user_id):
    require_admin(lock_actor(actor, user_id))
    user = User.objects.get(pk=user_id)
    user.is_active = False
    user.full_clean()
    user.save(update_fields=["is_active"])
    return user
