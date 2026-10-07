import pytest
from django.contrib.auth import SESSION_KEY
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, connection, transaction
from django.test import Client

from accounts.models import User
from tests.conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db


def login(client, user, **extra):
    return client.post("/login/", {"username": user.username, "password": TEST_PASSWORD, **extra})


def test_real_postgresql_backend():
    assert connection.vendor == "postgresql"


def test_password_is_hashed(user):
    user.refresh_from_db()
    assert user.password != TEST_PASSWORD
    assert user.check_password(TEST_PASSWORD)


@pytest.mark.parametrize("role", User.Role.values)
def test_shared_login_uses_persisted_role(client, role):
    user = User.objects.create_user(
        username=role, password=TEST_PASSWORD, role=role, must_change_password=False
    )
    response = login(client, user, role="ADMIN")
    assert response.status_code == 302
    assert response.url == "/"
    assert client.get("/api/auth/me/").json()["role"] == role
    assert user.get_role_display() in client.get("/").content.decode()


def test_superuser_is_admin():
    user = User.objects.create_superuser("owner", password=TEST_PASSWORD)
    assert user.role == User.Role.ADMIN
    assert user.is_staff and user.is_superuser
    assert not user.must_change_password


def test_non_admin_superuser_rejected():
    with pytest.raises(ValueError):
        User.objects.create_superuser("owner", password=TEST_PASSWORD, role=User.Role.EMPLOYEE)


@pytest.mark.parametrize(
    "changes",
    [
        {"role": "OWNER"},
        {"role": User.Role.EMPLOYEE, "is_staff": True},
        {"role": User.Role.PROJECT_MANAGER, "is_superuser": True},
    ],
)
def test_database_rejects_invalid_roles_and_privileges(user, changes):
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=user.pk).update(**changes)


def test_duplicate_identifier_rejected(user):
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(username=user.username, password=TEST_PASSWORD)


def test_anonymous_pages_and_api_denied(client):
    assert client.get("/").url == "/login/?next=/"
    assert client.get("/password/change/").status_code == 302
    assert client.get("/api/auth/me/").status_code == 403


def test_invalid_login_preserves_identifier_and_never_password(client, user):
    response = client.post("/login/", {"username": user.username, "password": "WrongSecret!"})
    html = response.content.decode()
    assert response.status_code == 200
    assert "The login identifier or password is incorrect." in html
    assert user.username in html
    assert "WrongSecret!" not in html
    assert SESSION_KEY not in client.session


def test_inactive_login_has_generic_error(client, user):
    user.is_active = False
    user.save(update_fields=["is_active"])
    response = login(client, user)
    assert "The login identifier or password is incorrect." in response.content.decode()
    assert SESSION_KEY not in client.session


def test_deactivation_revokes_existing_session(client, user):
    login(client, user)
    User.objects.filter(pk=user.pk).update(is_active=False)
    assert client.get("/").status_code == 302
    assert client.get("/api/auth/me/").status_code == 403


def test_login_requires_real_csrf(user):
    client = Client(enforce_csrf_checks=True)
    assert login(client, user).status_code == 403
    client.get("/login/")
    token = client.cookies["csrftoken"].value
    assert login(client, user, csrfmiddlewaretoken=token).status_code == 302


def test_logout_is_post_and_csrf_protected(user):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    assert client.get("/logout/").status_code == 405
    assert client.post("/logout/").status_code == 403
    client.get("/")
    token = client.cookies["csrftoken"].value
    response = client.post("/logout/", {"csrfmiddlewaretoken": token})
    assert response.status_code == 302 and response.url == "/login/"
    assert SESSION_KEY not in client.session
    assert client.get("/api/auth/me/").status_code == 403


@pytest.mark.parametrize("next_url", ["https://attacker.example/", "//attacker.example/"])
def test_external_login_redirect_rejected(client, user, next_url):
    assert login(client, user, next=next_url).url == "/"


def test_initial_password_blocks_pages_api_and_admin(client):
    user = User.objects.create_user("new", password=TEST_PASSWORD)
    assert login(client, user, next="/admin/").url == "/password/change/"
    assert client.get("/").url == "/password/change/"
    assert client.get("/admin/").url == "/password/change/"
    assert client.get("/api/auth/me/").status_code == 403
    assert client.get("/password/change/").status_code == 200
    assert client.post("/logout/").status_code == 302


def test_password_change_unlocks_account_and_invalidates_other_session(client):
    user = User.objects.create_user("new", password=TEST_PASSWORD)
    other = Client()
    login(client, user)
    login(other, user)
    response = client.post(
        "/password/change/",
        {
            "old_password": TEST_PASSWORD,
            "new_password1": "Updated-Secret!951",
            "new_password2": "Updated-Secret!951",
            "role": "ADMIN",
        },
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.check_password("Updated-Secret!951")
    assert not user.check_password(TEST_PASSWORD)
    assert not user.must_change_password
    assert user.role == User.Role.EMPLOYEE
    assert client.get("/api/auth/me/").status_code == 200
    assert other.get("/api/auth/me/").status_code == 403


@pytest.mark.parametrize(
    "old,new1,new2",
    [
        ("incorrect", "Updated-Secret!951", "Updated-Secret!951"),
        (TEST_PASSWORD, "123", "123"),
        (TEST_PASSWORD, "Updated-Secret!951", "Different-Secret!951"),
    ],
)
def test_invalid_password_change_keeps_initial_lock(client, old, new1, new2):
    user = User.objects.create_user("new", password=TEST_PASSWORD)
    login(client, user)
    response = client.post(
        "/password/change/",
        {
            "old_password": old,
            "new_password1": new1,
            "new_password2": new2,
        },
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.must_change_password and user.check_password(TEST_PASSWORD)
    assert new1 not in response.content.decode()


def test_password_change_requires_real_csrf(user):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    assert client.post("/password/change/", {}).status_code == 403


def test_identity_exposes_only_current_user_and_is_read_only(client, user):
    User.objects.create_user("other", password=TEST_PASSWORD)
    login(client, user)
    response = client.get("/api/auth/me/")
    assert response.json() == {
        "id": user.pk,
        "username": user.username,
        "name": "Asha Deshmukh",
        "role": "EMPLOYEE",
        "role_label": "Employee",
    }
    assert response["Cache-Control"] == "no-store"
    assert (
        client.patch(
            "/api/auth/me/", {"role": "ADMIN"}, content_type="application/json"
        ).status_code
        == 405
    )


def test_normal_users_cannot_access_django_admin(client, user):
    login(client, user)
    assert client.get("/admin/accounts/user/").status_code == 302
    assert client.post("/admin/accounts/user/add/", {"username": "intruder"}).status_code == 302
    assert not User.objects.filter(username="intruder").exists()


def test_superuser_can_create_manager_in_development_admin(client):
    admin = User.objects.create_superuser("owner", password=TEST_PASSWORD)
    client.force_login(admin)
    response = client.post(
        "/admin/accounts/user/add/",
        {
            "username": "manager",
            "password1": TEST_PASSWORD,
            "password2": TEST_PASSWORD,
            "usable_password": "true",
            "role": "PROJECT_MANAGER",
            "first_name": "New",
        },
    )
    assert response.status_code == 302
    user = User.objects.get(username="manager")
    assert user.role == "PROJECT_MANAGER" and user.must_change_password
    assert user.check_password(TEST_PASSWORD) and not user.is_staff


def test_admin_password_reset_requires_change(client, user):
    admin = User.objects.create_superuser("owner", password=TEST_PASSWORD)
    client.force_login(admin)
    response = client.post(
        f"/admin/accounts/user/{user.pk}/password/",
        {
            "password1": "Reset-Secret!752",
            "password2": "Reset-Secret!752",
            "usable_password": "true",
        },
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.must_change_password and user.check_password("Reset-Secret!752")


def test_seed_is_idempotent_and_preserves_existing_passwords(settings):
    settings.DEBUG = True
    settings.DEMO_PASSWORD = TEST_PASSWORD
    call_command("seed_demo")
    user = User.objects.get(username="asha@demo.local")
    user.set_password("Changed-Secret!437")
    user.save(update_fields=["password"])
    count = User.objects.count()
    call_command("seed_demo")
    assert User.objects.count() == count == 7
    user.refresh_from_db()
    assert user.check_password("Changed-Secret!437")
    assert not User.objects.get(username="meera@demo.local").is_active


def test_seed_refuses_production(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError, match="only available"):
        call_command("seed_demo")
