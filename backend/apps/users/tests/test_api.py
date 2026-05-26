import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="test@example.com",
        username="testuser",
        password="StrongPass123!",
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


@pytest.mark.django_db
class TestRegister:
    def test_register_valid(self, client):
        r = client.post(
            "/api/v1/auth/register/",
            {"email": "new@example.com", "username": "newuser", "password": "StrongPass123!", "password_confirm": "StrongPass123!"},
            format="json",
        )
        assert r.status_code == 201
        assert "access" in r.data
        assert r.data["user"]["email"] == "new@example.com"

    def test_register_duplicate_email(self, client, user):
        r = client.post(
            "/api/v1/auth/register/",
            {"email": "test@example.com", "username": "other", "password": "StrongPass123!", "password_confirm": "StrongPass123!"},
            format="json",
        )
        assert r.status_code == 400

    def test_register_password_mismatch(self, client):
        r = client.post(
            "/api/v1/auth/register/",
            {"email": "x@x.com", "username": "x", "password": "StrongPass123!", "password_confirm": "WrongPass456!"},
            format="json",
        )
        assert r.status_code == 400
        assert "password_confirm" in r.data


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

    def test_logout(self, auth_client):
        r = auth_client.post("/api/v1/auth/logout/")
        assert r.status_code == 204
