from http.cookies import Morsel

import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from backend.apps.identity.models import Role, RoleCode, User, UserRole, UserStatus
from backend.apps.identity.services.bootstrap import seed_identity_rbac

pytestmark = pytest.mark.django_db

PASSWORD = "test-password"


def user(email: str, status: str = UserStatus.ACTIVE) -> User:
    return User.objects.create_user(
        email,
        PASSWORD,
        first_name="Test",
        last_name="User",
        status=status,
    )


def csrf_client() -> tuple[APIClient, str]:
    client = APIClient(enforce_csrf_checks=True)
    response = client.get(reverse("csrf-cookie"))
    assert response.status_code == 204
    return client, client.cookies[settings.CSRF_COOKIE_NAME].value


def login(client: APIClient, csrf: str, account: User):
    return client.post(
        reverse("token-obtain-pair"),
        {"email": account.email, "password": PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )


def assert_error_envelope(response, status_code: int) -> None:
    assert response.status_code == status_code
    assert set(response.json()) == {"error"}
    assert set(response.json()["error"]) == {"code", "message", "details"}


def assert_blacklisted(refresh: str) -> None:
    assert BlacklistedToken.objects.filter(token__token=refresh).exists()


def test_login_requires_csrf_and_returns_refresh_only_as_hardened_cookie() -> None:
    account = user("active@example.test")
    unprotected = APIClient(enforce_csrf_checks=True).post(
        reverse("token-obtain-pair"),
        {"email": account.email, "password": PASSWORD},
        format="json",
    )
    assert_error_envelope(unprotected, 403)

    client, csrf = csrf_client()
    response = login(client, csrf, account)

    assert response.status_code == 200
    assert set(response.json()) == {"access"}
    cookie: Morsel[str] = response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]
    assert cookie["httponly"] is True
    assert cookie["secure"] is settings.AUTH_COOKIE_SECURE
    assert cookie["samesite"] == settings.AUTH_COOKIE_SAMESITE
    assert cookie["path"] == settings.AUTH_REFRESH_COOKIE_PATH


def test_pending_account_cannot_login_until_an_admin_activates_it() -> None:
    seed_identity_rbac()
    admin = user("admin@example.test")
    UserRole.objects.create(user=admin, role=Role.objects.get(code=RoleCode.ADMIN))
    pending = user("pending@example.test", UserStatus.PENDING)
    admin_client, admin_csrf = csrf_client()
    admin_access = login(admin_client, admin_csrf, admin).json()["access"]
    admin_client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_access}")

    pending_client, pending_csrf = csrf_client()
    assert_error_envelope(login(pending_client, pending_csrf, pending), 401)

    response = admin_client.post(
        reverse("user-status", args=(pending.id,)),
        {"status": UserStatus.ACTIVE},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == UserStatus.ACTIVE
    assert login(pending_client, pending_csrf, pending).status_code == 200


def test_refresh_rotates_cookie_and_logout_blacklists_and_clears_it() -> None:
    account = user("refresh@example.test")
    client, csrf = csrf_client()
    login_response = login(client, csrf, account)
    access = login_response.json()["access"]
    original_refresh = client.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value

    without_csrf = client.post(reverse("token-refresh"), format="json")
    assert_error_envelope(without_csrf, 403)

    refresh_response = client.post(reverse("token-refresh"), format="json", HTTP_X_CSRFTOKEN=csrf)
    assert refresh_response.status_code == 200
    assert set(refresh_response.json()) == {"access"}
    rotated_refresh = client.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value
    assert rotated_refresh != original_refresh
    assert_blacklisted(original_refresh)

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    logout_response = client.post(
        reverse("logout"),
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert logout_response.status_code == 204
    assert logout_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]["max-age"] == 0
    assert_blacklisted(rotated_refresh)
    assert_error_envelope(
        client.post(reverse("token-refresh"), format="json", HTTP_X_CSRFTOKEN=csrf),
        401,
    )

    client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = "invalid"
    repeated_logout = client.post(reverse("logout"), format="json", HTTP_X_CSRFTOKEN=csrf)
    assert repeated_logout.status_code == 204
    assert repeated_logout.cookies[settings.AUTH_REFRESH_COOKIE_NAME]["max-age"] == 0


def test_status_change_requires_custom_rbac_and_invalidates_credentials() -> None:
    seed_identity_rbac()
    admin = user("status-admin@example.test")
    member = user("member@example.test")
    target = user("target@example.test")
    UserRole.objects.create(user=admin, role=Role.objects.get(code=RoleCode.ADMIN))

    admin_client, admin_csrf = csrf_client()
    admin_access = login(admin_client, admin_csrf, admin).json()["access"]
    admin_client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_access}")
    member_client, member_csrf = csrf_client()
    member_access = login(member_client, member_csrf, member).json()["access"]
    member_client.credentials(HTTP_AUTHORIZATION=f"Bearer {member_access}")
    target_client, target_csrf = csrf_client()
    target_login = login(target_client, target_csrf, target)
    target_access = target_login.json()["access"]
    target_client.credentials(HTTP_AUTHORIZATION=f"Bearer {target_access}")
    target_refresh = target_client.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value

    denied = member_client.post(
        reverse("user-status", args=(target.id,)),
        {"status": UserStatus.SUSPENDED},
        format="json",
    )
    assert_error_envelope(denied, 403)

    profile_patch = admin_client.patch(
        reverse("user-detail", args=(target.id,)),
        {"status": UserStatus.DISABLED, "first_name": "Renamed"},
        format="json",
    )
    assert profile_patch.status_code == 200
    target.refresh_from_db()
    assert target.status == UserStatus.ACTIVE
    assert target.first_name == "Renamed"

    changed = admin_client.post(
        reverse("user-status", args=(target.id,)),
        {"status": UserStatus.SUSPENDED},
        format="json",
    )
    assert changed.status_code == 200
    assert_blacklisted(target_refresh)

    assert_error_envelope(
        target_client.get(reverse("user-me")),
        401,
    )
    assert_error_envelope(
        target_client.post(reverse("token-refresh"), format="json", HTTP_X_CSRFTOKEN=target_csrf),
        401,
    )
    assert_error_envelope(
        APIClient().post(reverse("token-verify"), {"token": target_access}, format="json"),
        401,
    )
