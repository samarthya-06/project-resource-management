import pytest
from django.core.management import call_command
from django.test import override_settings

from accounts.models import User

TEST_PASSWORD = "Foundation-Local!482"


@pytest.fixture(scope="session", autouse=True)
def collected_staticfiles(tmp_path_factory):
    # Production-template and WhiteNoise tests need a real hashed asset manifest.
    # Build it once without relying on, or overwriting, local collected assets.
    static_root = tmp_path_factory.mktemp("collected-staticfiles")
    with override_settings(STATIC_ROOT=static_root):
        call_command("collectstatic", interactive=False, verbosity=0)
        yield static_root


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="asha@demo.local",
        password=TEST_PASSWORD,
        first_name="Asha",
        last_name="Deshmukh",
        must_change_password=False,
    )
