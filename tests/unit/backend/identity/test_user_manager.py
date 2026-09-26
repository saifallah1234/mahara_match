import pytest

from backend.apps.identity.models import User

pytestmark = pytest.mark.unit


def test_create_user_matches_the_email_only_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(User, "save", lambda self, **kwargs: None)
    user = User.objects.create_user(
        email=" Person@Example.com ",
        password="test-password",
        first_name=" Ada ",
        last_name=" Lovelace ",
    )
    assert user.email == "person@example.com"
    assert user.first_name == "Ada"
    assert user.last_name == "Lovelace"
    assert user.check_password("test-password")


def test_create_superuser_accepts_required_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(User, "save", lambda self, **kwargs: None)
    user = User.objects.create_superuser(
        email="admin@example.com",
        password="test-password",
        first_name="Admin",
        last_name="User",
    )
    assert user.is_staff and user.is_superuser and user.is_active
