from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.inventory.tests.factories import ProductFactory, UserFactory
from apps.orders.tests.factories import PurchaseOrderFactory, SalesOrderFactory
from apps.orders.services import confirm_purchase_order, confirm_sales_order


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    token = AccessToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def _confirmed_po(product, qty, cost):
    po = PurchaseOrderFactory(owner=product.owner, product=product, quantity=qty, cost_per_unit=cost)
    return confirm_purchase_order(po, f"LOT-{po.pk}")


@pytest.mark.django_db
class TestFinancialSummaryView:
    def test_auth_required(self):
        resp = APIClient().get(reverse("financials-summary"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_returns_zeros(self, auth_client):
        resp = auth_client.get(reverse("financials-summary"))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["total_cost"] == "0.00"
        assert data["total_revenue"] == "0.00"
        assert data["total_profit"] == "0.00"

    def test_summary_reflects_confirmed_orders(self, auth_client, user):
        product = ProductFactory(owner=user)
        po = _confirmed_po(product, Decimal("100"), Decimal("2.00"))
        so = SalesOrderFactory(
            owner=user, product=product, stock=po.stock,
            quantity=Decimal("100"), price_per_unit=Decimal("5.00"),
        )
        confirm_sales_order(so)

        resp = auth_client.get(reverse("financials-summary"))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert Decimal(data["total_cost"]) == Decimal("200.00")
        assert Decimal(data["total_revenue"]) == Decimal("500.00")
        assert Decimal(data["total_profit"]) == Decimal("300.00")

    def test_data_isolation(self, auth_client, user):
        other = UserFactory()
        other_product = ProductFactory(owner=other)
        _confirmed_po(other_product, Decimal("999"), Decimal("999"))

        resp = auth_client.get(reverse("financials-summary"))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert Decimal(data["total_cost"]) == Decimal("0.00")


@pytest.mark.django_db
class TestProductFinancialsView:
    def test_auth_required(self):
        resp = APIClient().get(reverse("financials-products"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_list_with_correct_shape(self, auth_client, user):
        ProductFactory(owner=user)
        resp = auth_client.get(reverse("financials-products"))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        row = data[0]
        for key in ("product_id", "product_name", "sku", "total_cost", "total_revenue", "profit", "margin_pct"):
            assert key in row, f"Missing key: {key}"

    def test_profit_calculation(self, auth_client, user):
        product = ProductFactory(owner=user)
        po = _confirmed_po(product, Decimal("50"), Decimal("4.00"))
        so = SalesOrderFactory(
            owner=user, product=product, stock=po.stock,
            quantity=Decimal("50"), price_per_unit=Decimal("10.00"),
        )
        confirm_sales_order(so)

        resp = auth_client.get(reverse("financials-products"))
        assert resp.status_code == status.HTTP_200_OK
        row = resp.json()[0]
        assert Decimal(row["total_cost"]) == Decimal("200.00")
        assert Decimal(row["total_revenue"]) == Decimal("500.00")
        assert Decimal(row["profit"]) == Decimal("300.00")

    def test_draft_orders_excluded(self, auth_client, user):
        product = ProductFactory(owner=user)
        PurchaseOrderFactory(owner=user, product=product, quantity=Decimal("100"), cost_per_unit=Decimal("5.00"))
        resp = auth_client.get(reverse("financials-products"))
        row = resp.json()[0]
        assert Decimal(row["total_cost"]) == Decimal("0.00")

    def test_data_isolation(self, auth_client, user):
        other = UserFactory()
        other_product = ProductFactory(owner=other)
        _confirmed_po(other_product, Decimal("100"), Decimal("10"))

        resp = auth_client.get(reverse("financials-products"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()) == 0
