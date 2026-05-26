import pytest
from rest_framework.test import APIClient

from .factories import ProductFactory, StockFactory, UserFactory


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def other_user(db):
    return UserFactory()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestProductDataIsolation:
    def test_user_sees_only_own_products(self, auth_client, user, other_user):
        ProductFactory(owner=user)
        ProductFactory(owner=other_user)
        r = auth_client.get("/api/v1/products/")
        assert r.status_code == 200
        assert r.data["count"] == 1

    def test_cannot_access_other_users_product(self, auth_client, other_user):
        product = ProductFactory(owner=other_user)
        r = auth_client.get(f"/api/v1/products/{product.pk}/")
        assert r.status_code == 404

    def test_cannot_update_other_users_product(self, auth_client, other_user):
        product = ProductFactory(owner=other_user)
        r = auth_client.patch(f"/api/v1/products/{product.pk}/", {"name": "Hacked"}, format="json")
        assert r.status_code == 404

    def test_cannot_delete_other_users_product(self, auth_client, other_user):
        product = ProductFactory(owner=other_user)
        r = auth_client.delete(f"/api/v1/products/{product.pk}/")
        assert r.status_code == 404


@pytest.mark.django_db
class TestProductCRUD:
    def test_create_product(self, auth_client, user):
        r = auth_client.post(
            "/api/v1/products/",
            {"name": "Oat Milk", "sku": "OAT-001", "unit_type": "l", "description": ""},
            format="json",
        )
        assert r.status_code == 201
        assert r.data["sku"] == "OAT-001"

    def test_sku_normalised_uppercase(self, auth_client):
        r = auth_client.post(
            "/api/v1/products/",
            {"name": "Test", "sku": "oat-001", "unit_type": "count"},
            format="json",
        )
        assert r.status_code == 201
        assert r.data["sku"] == "OAT-001"

    def test_duplicate_sku_rejected(self, auth_client, user):
        ProductFactory(owner=user, sku="DUP-001")
        r = auth_client.post(
            "/api/v1/products/",
            {"name": "Another", "sku": "DUP-001", "unit_type": "count"},
            format="json",
        )
        assert r.status_code == 400

    def test_search_by_name(self, auth_client, user):
        ProductFactory(owner=user, name="Oat Milk")
        ProductFactory(owner=user, name="Almond Milk")
        r = auth_client.get("/api/v1/products/?search=Oat")
        assert r.data["count"] == 1
        assert r.data["results"][0]["name"] == "Oat Milk"

    def test_filter_by_unit_type(self, auth_client, user):
        ProductFactory(owner=user, unit_type="l")
        ProductFactory(owner=user, unit_type="count")
        r = auth_client.get("/api/v1/products/?unit_type=l")
        assert r.data["count"] == 1

    def test_total_stock_annotation(self, auth_client, user):
        product = ProductFactory(owner=user)
        StockFactory(product=product, owner=user, quantity=10)
        StockFactory(product=product, owner=user, quantity=5)
        r = auth_client.get(f"/api/v1/products/{product.pk}/")
        assert float(r.data["total_stock"]) == 15.0


@pytest.mark.django_db
class TestStockDataIsolation:
    def test_user_sees_only_own_stock(self, auth_client, user, other_user):
        StockFactory(owner=user, product=ProductFactory(owner=user))
        StockFactory(owner=other_user, product=ProductFactory(owner=other_user))
        r = auth_client.get("/api/v1/stock/")
        assert r.data["count"] == 1

    def test_cannot_access_other_users_stock(self, auth_client, other_user):
        stock = StockFactory(owner=other_user, product=ProductFactory(owner=other_user))
        r = auth_client.get(f"/api/v1/stock/{stock.pk}/")
        assert r.status_code == 404
