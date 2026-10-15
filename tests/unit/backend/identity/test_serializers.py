import pytest

from backend.apps.identity.api.users_serializers import (
    UserCreateSerializer,
    UserProfileUpdateSerializer,
    UserReadSerializer,
    UserStatusUpdateSerializer,
)

pytestmark = pytest.mark.unit


def test_user_create_serializer_does_not_accept_protected_fields() -> None:
    serializer = UserCreateSerializer()
    assert set(serializer.fields) == {"email", "password", "first_name", "last_name", "phone"}


def test_profile_update_serializer_only_accepts_profile_fields() -> None:
    serializer = UserProfileUpdateSerializer()
    assert set(serializer.fields) == {"first_name", "last_name", "phone"}


def test_status_update_uses_a_separate_privileged_contract() -> None:
    assert set(UserStatusUpdateSerializer().fields) == {"status"}


def test_user_read_serializer_never_exposes_credentials_or_technical_flags() -> None:
    serializer = UserReadSerializer()
    assert "password" not in serializer.fields
    assert "is_staff" not in serializer.fields
    assert "is_superuser" not in serializer.fields
