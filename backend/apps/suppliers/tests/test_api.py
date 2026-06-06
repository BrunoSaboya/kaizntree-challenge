import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.inventory.tests.factories import OrganizationFactory, UserFactory
from apps.suppliers.models import Supplier


@pytest.fixture
def client():
    return APIClient()


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
def auth_client(client, user):
    from rest_framework_simplejwt.tokens import AccessToken
    token = AccessToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def supplier(user, org):
    return Supplier.objects.create(
        organization=org,
        name="Acme Farms",
        email="orders@acmefarms.com",
        phone="+1-555-0100",
        payment_terms="Net30",
        lead_time_days=7,
    )


@pytest.mark.django_db
class TestSupplierCRUD:
    def test_list_suppliers(self, auth_client, supplier):
        resp = auth_client.get(reverse("supplier-list"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["name"] == "Acme Farms"

    def test_create_supplier(self, auth_client):
        resp = auth_client.post(reverse("supplier-list"), {
            "name": "Green Valley Co",
            "email": "info@greenvalley.com",
            "lead_time_days": 14,
            "payment_terms": "Net60",
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "Green Valley Co"
        assert resp.data["lead_time_days"] == 14

    def test_retrieve_supplier(self, auth_client, supplier):
        resp = auth_client.get(reverse("supplier-detail", args=[supplier.pk]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["payment_terms"] == "Net30"

    def test_update_supplier(self, auth_client, supplier):
        resp = auth_client.patch(
            reverse("supplier-detail", args=[supplier.pk]),
            {"lead_time_days": 10},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["lead_time_days"] == 10

    def test_delete_supplier(self, auth_client, supplier):
        resp = auth_client.delete(reverse("supplier-detail", args=[supplier.pk]))
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Supplier.objects.filter(pk=supplier.pk).exists()

    def test_name_stripped_on_create(self, auth_client):
        resp = auth_client.post(reverse("supplier-list"), {"name": "  Organic Co  "}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "Organic Co"

    def test_filter_by_active(self, auth_client, user, org):
        Supplier.objects.create(organization=org, name="Active Co", active=True)
        Supplier.objects.create(organization=org, name="Inactive Co", active=False)
        resp = auth_client.get(reverse("supplier-list") + "?active=true")
        assert resp.status_code == status.HTTP_200_OK
        names = [s["name"] for s in resp.data["results"]]
        assert "Active Co" in names
        assert "Inactive Co" not in names


@pytest.mark.django_db
class TestSupplierDataIsolation:
    def test_cannot_see_other_org_suppliers(self, auth_client, user):
        other_org = OrganizationFactory()
        Supplier.objects.create(organization=other_org, name="Other Corp")
        resp = auth_client.get(reverse("supplier-list"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 0

    def test_cannot_access_other_org_supplier_detail(self, auth_client, user):
        other_org = OrganizationFactory()
        other_supplier = Supplier.objects.create(organization=other_org, name="Other Corp")
        resp = auth_client.get(reverse("supplier-detail", args=[other_supplier.pk]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_rejected(self, client):
        resp = client.get(reverse("supplier-list"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
