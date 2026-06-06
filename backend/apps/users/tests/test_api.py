import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.inventory.tests.factories import AdminUserFactory, OrganizationFactory, UserFactory

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def org(db):
    return OrganizationFactory()


@pytest.fixture
def user(db, org):
    u = User.objects.create_user(
        email="test@example.com",
        username="testuser",
        password="StrongPass123!",
        role=User.ROLE_OWNER,
        organization=org,
    )
    org.owner = u
    org.save()
    return u


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@example.com",
        username="adminuser",
        password="StrongPass123!",
        role=User.ROLE_ADMIN,
        organization=None,
        is_staff=True,
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    response = client.post(
        "/api/v1/auth/login/",
        {"email": "test@example.com", "password": "StrongPass123!"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    response = client.post(
        "/api/v1/auth/login/",
        {"email": "admin@example.com", "password": "StrongPass123!"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client


@pytest.mark.django_db
class TestRegister:
    def test_register_anonymous_is_forbidden(self, client):
        r = client.post(
            "/api/v1/auth/register/",
            {"email": "new@example.com", "username": "newuser",
             "password": "StrongPass123!", "password_confirm": "StrongPass123!"},
            format="json",
        )
        assert r.status_code == 401

    def test_non_admin_register_is_forbidden(self, auth_client, org):
        r = auth_client.post(
            "/api/v1/auth/register/",
            {"email": "new@example.com", "username": "newuser",
             "password": "StrongPass123!", "password_confirm": "StrongPass123!",
             "role": "owner", "organization": org.pk},
            format="json",
        )
        assert r.status_code == 403

    def test_admin_can_create_user(self, admin_client, org):
        r = admin_client.post(
            "/api/v1/auth/register/",
            {"email": "new@example.com", "username": "newuser",
             "password": "StrongPass123!", "password_confirm": "StrongPass123!",
             "role": "owner", "organization": org.pk},
            format="json",
        )
        assert r.status_code == 201
        assert r.data["email"] == "new@example.com"
        assert r.data["role"] == "owner"


@pytest.mark.django_db
class TestLogin:
    def test_login_valid(self, client, user):
        r = client.post(
            "/api/v1/auth/login/",
            {"email": "test@example.com", "password": "StrongPass123!"},
            format="json",
        )
        assert r.status_code == 200
        assert "access" in r.data
        assert "refresh" not in r.data  # refresh is in cookie, not body
        assert "user" in r.data
        assert r.data["user"]["role"] == "owner"

    def test_login_wrong_password(self, client, user):
        r = client.post(
            "/api/v1/auth/login/",
            {"email": "test@example.com", "password": "wrongpass"},
            format="json",
        )
        assert r.status_code == 401

    def test_me_requires_auth(self, client):
        r = client.get("/api/v1/auth/me/")
        assert r.status_code == 401

    def test_me_returns_user(self, auth_client, user):
        r = auth_client.get("/api/v1/auth/me/")
        assert r.status_code == 200
        assert r.data["email"] == user.email
        assert r.data["role"] == user.role
        assert r.data["organization_id"] == user.organization_id

    def test_logout(self, auth_client):
        r = auth_client.post("/api/v1/auth/logout/")
        assert r.status_code == 204


@pytest.mark.django_db
class TestMeUpdate:
    def test_self_can_update_first_last_name(self, auth_client, user):
        r = auth_client.patch(
            "/api/v1/auth/me/",
            {"first_name": "Alice", "last_name": "Smith"},
            format="json",
        )
        assert r.status_code == 200
        user.refresh_from_db()
        assert user.first_name == "Alice"

    def test_self_cannot_change_role(self, auth_client, user):
        r = auth_client.patch(
            "/api/v1/auth/me/",
            {"role": "admin"},
            format="json",
        )
        # Either 400 or the field is ignored — role should remain unchanged
        user.refresh_from_db()
        assert user.role != "admin"


@pytest.mark.django_db
class TestAdminUserViewSet:
    def test_admin_can_list_users(self, admin_client, user):
        r = admin_client.get("/api/v1/users/")
        assert r.status_code == 200
        assert any(u["email"] == user.email for u in r.data["results"])

    def test_non_admin_cannot_list_users(self, auth_client):
        r = auth_client.get("/api/v1/users/")
        assert r.status_code == 403

    def test_admin_can_deactivate_user(self, admin_client, user):
        r = admin_client.delete(f"/api/v1/users/{user.pk}/")
        assert r.status_code == 204
        user.refresh_from_db()
        assert user.is_active is False

    def test_hard_delete_removes_user(self, admin_client, db, org):
        member = User.objects.create_user(
            email="todelete@example.com", username="todelete",
            password="StrongPass123!", role=User.ROLE_MEMBER, organization=org,
        )
        r = admin_client.delete(f"/api/v1/users/{member.pk}/hard-delete/")
        assert r.status_code == 204
        assert not User.objects.filter(pk=member.pk).exists()

    def test_hard_delete_blocked_for_self(self, admin_client, admin_user):
        r = admin_client.delete(f"/api/v1/users/{admin_user.pk}/hard-delete/")
        assert r.status_code == 400
        assert "own account" in r.data["detail"]

    def test_hard_delete_blocked_for_another_admin(self, admin_client, db):
        other_admin = User.objects.create_user(
            email="other_admin@example.com", username="otheradmin",
            password="StrongPass123!", role=User.ROLE_ADMIN, organization=None,
        )
        r = admin_client.delete(f"/api/v1/users/{other_admin.pk}/hard-delete/")
        assert r.status_code == 400

    def test_hard_delete_blocked_when_owns_org(self, admin_client, user):
        r = admin_client.delete(f"/api/v1/users/{user.pk}/hard-delete/")
        assert r.status_code == 409
        assert "organization" in r.data["detail"].lower()


@pytest.mark.django_db
class TestOrgViewSet:
    def test_admin_can_list_orgs(self, admin_client, org):
        r = admin_client.get("/api/v1/organizations/")
        assert r.status_code == 200

    def test_non_admin_cannot_list_orgs(self, auth_client):
        r = auth_client.get("/api/v1/organizations/")
        assert r.status_code == 403

    def test_delete_org_blocked_when_has_active_members(self, admin_client, org, user):
        r = admin_client.delete(f"/api/v1/organizations/{org.pk}/")
        assert r.status_code == 409
        assert "active member" in r.data["detail"].lower()

    def test_delete_org_success(self, admin_client, db):
        from apps.users.models import Organization
        empty_org = Organization.objects.create(name="Empty Org")
        r = admin_client.delete(f"/api/v1/organizations/{empty_org.pk}/")
        assert r.status_code == 204
        assert not Organization.objects.filter(pk=empty_org.pk).exists()


@pytest.mark.django_db
class TestOrgMemberViewSet:
    def test_owner_can_list_members(self, auth_client):
        r = auth_client.get("/api/v1/org/members/")
        assert r.status_code == 200

    def test_admin_cannot_list_members(self, admin_client):
        r = admin_client.get("/api/v1/org/members/")
        assert r.status_code == 403

    def test_owner_can_create_member(self, auth_client, org):
        r = auth_client.post(
            "/api/v1/org/members/",
            {"email": "member@example.com", "username": "member1",
             "password": "StrongPass123!"},
            format="json",
        )
        assert r.status_code == 201
        new_user = User.objects.get(email="member@example.com")
        assert new_user.role == User.ROLE_MEMBER
        assert new_user.organization == org
