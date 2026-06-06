import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.users.models import Organization
from .factories import OrganizationFactory, ProductFactory, StockFactory, UserFactory

User = get_user_model()


@pytest.fixture
def org(db):
    return OrganizationFactory()


@pytest.fixture
def user(db, org):
    u = UserFactory(organization=org)
    org.owner = u
    org.save()
    return u


@pytest.fixture
def other_org(db):
    return OrganizationFactory()


@pytest.fixture
def other_user(db, other_org):
    u = UserFactory(organization=other_org)
    other_org.owner = u
    other_org.save()
    return u


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestProductDataIsolation:
    def test_org_members_share_products(self, auth_client, user, org):
        # A second member in the same org — their products ARE visible to user
        member = UserFactory(organization=org, role=User.ROLE_MEMBER)
        ProductFactory(organization=org)
        ProductFactory(organization=org)
        r = auth_client.get("/api/v1/products/")
        assert r.status_code == 200
        assert r.data["count"] == 2

    def test_cross_org_isolation(self, auth_client, other_org):
        ProductFactory(organization=other_org)
        r = auth_client.get("/api/v1/products/")
        assert r.status_code == 200
        assert r.data["count"] == 0

    def test_cannot_access_other_org_product(self, auth_client, other_org):
        product = ProductFactory(organization=other_org)
        r = auth_client.get(f"/api/v1/products/{product.pk}/")
        assert r.status_code == 404

    def test_cannot_update_other_org_product(self, auth_client, other_org):
        product = ProductFactory(organization=other_org)
        r = auth_client.patch(f"/api/v1/products/{product.pk}/", {"name": "Hacked"}, format="json")
        assert r.status_code == 404

    def test_cannot_delete_other_org_product(self, auth_client, other_org):
        product = ProductFactory(organization=other_org)
        r = auth_client.delete(f"/api/v1/products/{product.pk}/")
        assert r.status_code == 404

    def test_admin_cannot_access_products(self, db):
        from apps.inventory.tests.factories import AdminUserFactory
        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)
        r = client.get("/api/v1/products/")
        assert r.status_code == 403


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

    def test_duplicate_sku_rejected(self, auth_client, user, org):
        ProductFactory(organization=org, sku="DUP-001")
        r = auth_client.post(
            "/api/v1/products/",
            {"name": "Another", "sku": "DUP-001", "unit_type": "count"},
            format="json",
        )
        assert r.status_code == 400

    def test_search_by_name(self, auth_client, user, org):
        ProductFactory(organization=org, name="Oat Milk")
        ProductFactory(organization=org, name="Almond Milk")
        r = auth_client.get("/api/v1/products/?search=Oat")
        assert r.data["count"] == 1
        assert r.data["results"][0]["name"] == "Oat Milk"

    def test_filter_by_unit_type(self, auth_client, user, org):
        ProductFactory(organization=org, unit_type="l")
        ProductFactory(organization=org, unit_type="count")
        r = auth_client.get("/api/v1/products/?unit_type=l")
        assert r.data["count"] == 1

    def test_total_stock_annotation(self, auth_client, user, org):
        product = ProductFactory(organization=org)
        StockFactory(product=product, organization=org, quantity=10)
        StockFactory(product=product, organization=org, quantity=5)
        r = auth_client.get(f"/api/v1/products/{product.pk}/")
        assert float(r.data["total_stock"]) == 15.0


@pytest.mark.django_db
class TestStockDataIsolation:
    def test_org_members_share_stock(self, auth_client, user, org):
        product = ProductFactory(organization=org)
        StockFactory(organization=org, product=product)
        r = auth_client.get("/api/v1/stock/")
        assert r.data["count"] == 1

    def test_cannot_access_other_org_stock(self, auth_client, other_org):
        stock = StockFactory(organization=other_org, product=ProductFactory(organization=other_org))
        r = auth_client.get(f"/api/v1/stock/{stock.pk}/")
        assert r.status_code == 404
