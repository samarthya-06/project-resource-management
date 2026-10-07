import pytest

from accounts.models import User

TEST_PASSWORD = "Foundation-Local!482"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="asha@demo.local",
        password=TEST_PASSWORD,
        first_name="Asha",
        last_name="Deshmukh",
        must_change_password=False,
    )
