from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.inventory.tests.factories import ProductFactory, StockFactory, UserFactory
from apps.orders.models import OrderStatus, PurchaseOrder, SalesOrder
from apps.orders.services import confirm_purchase_order

from .factories import PurchaseOrderFactory, SalesOrderFactory


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    token = AccessToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.mark.django_db
class TestPurchaseOrderViewSet:
    def test_list_requires_auth(self):
        resp = APIClient().get(reverse("purchase-order-list"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_own_orders(self, auth_client, user):
        PurchaseOrderFactory(owner=user, product=ProductFactory(owner=user))
        PurchaseOrderFactory(owner=user, product=ProductFactory(owner=user))
        resp = auth_client.get(reverse("purchase-order-list"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 2

    def test_create_draft_order(self, auth_client, user):
        product = ProductFactory(owner=user)
        resp = auth_client.post(reverse("purchase-order-list"), {
            "product": product.pk,
            "quantity": "50.000",
            "cost_per_unit": "3.5000",
            "order_date": "2025-03-01",
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["status"] == OrderStatus.DRAFT

    def test_confirm_purchase_order_creates_stock(self, auth_client, user):
        product = ProductFactory(owner=user)
        po = PurchaseOrderFactory(owner=user, product=product, quantity=Decimal("100"))
        resp = auth_client.post(
            reverse("purchase-order-confirm", args=[po.pk]),
            {"stock_identifier": "LOT-API-001"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == OrderStatus.CONFIRMED
        po.refresh_from_db()
        assert po.stock is not None
        assert po.stock.quantity == Decimal("100")

    def test_cancel_draft_order(self, auth_client, user):
        po = PurchaseOrderFactory(owner=user, product=ProductFactory(owner=user))
        resp = auth_client.post(reverse("purchase-order-cancel", args=[po.pk]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == OrderStatus.CANCELLED

    def test_delete_only_draft(self, auth_client, user):
        product = ProductFactory(owner=user)
        po = PurchaseOrderFactory(owner=user, product=product)
        po = confirm_purchase_order(po, "LOT-DEL")
        resp = auth_client.delete(reverse("purchase-order-detail", args=[po.pk]))
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_filter_by_status(self, auth_client, user):
        product = ProductFactory(owner=user)
        PurchaseOrderFactory(owner=user, product=product, status=OrderStatus.DRAFT)
        po2 = PurchaseOrderFactory(owner=user, product=product)
        confirm_purchase_order(po2, "LOT-FILTER")

        resp = auth_client.get(reverse("purchase-order-list") + "?status=draft")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["status"] == "draft"

    def test_data_isolation(self, auth_client, user):
        other = UserFactory()
        PurchaseOrderFactory(owner=other, product=ProductFactory(owner=other))
        resp = auth_client.get(reverse("purchase-order-list"))
        assert resp.data["count"] == 0

    def test_cross_user_detail_returns_404(self, auth_client):
        other = UserFactory()
        po = PurchaseOrderFactory(owner=other, product=ProductFactory(owner=other))
        resp = auth_client.get(reverse("purchase-order-detail", args=[po.pk]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestSalesOrderViewSet:
    def test_list_requires_auth(self):
        resp = APIClient().get(reverse("sales-order-list"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_own_orders(self, auth_client, user):
        product = ProductFactory(owner=user)
        stock = StockFactory(owner=user, product=product, quantity=Decimal("200"))
        SalesOrderFactory(owner=user, product=product, stock=stock)
        resp = auth_client.get(reverse("sales-order-list"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 1

    def test_create_sales_order(self, auth_client, user):
        product = ProductFactory(owner=user)
        stock = StockFactory(owner=user, product=product, quantity=Decimal("200"))
        resp = auth_client.post(reverse("sales-order-list"), {
            "product": product.pk,
            "stock": stock.pk,
            "quantity": "10.000",
            "price_per_unit": "25.0000",
            "order_date": "2025-03-01",
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["status"] == OrderStatus.DRAFT

    def test_confirm_sales_order_decrements_stock(self, auth_client, user):
        product = ProductFactory(owner=user)
        stock = StockFactory(owner=user, product=product, quantity=Decimal("100"))
        so = SalesOrderFactory(
            owner=user, product=product, stock=stock, quantity=Decimal("30")
        )
        resp = auth_client.post(reverse("sales-order-confirm", args=[so.pk]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == OrderStatus.CONFIRMED
        stock.refresh_from_db()
        assert stock.quantity == Decimal("70")

    def test_confirm_fails_insufficient_stock(self, auth_client, user):
        product = ProductFactory(owner=user)
        stock = StockFactory(owner=user, product=product, quantity=Decimal("5"))
        so = SalesOrderFactory(
            owner=user, product=product, stock=stock, quantity=Decimal("100")
        )
        resp = auth_client.post(reverse("sales-order-confirm", args=[so.pk]))
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancel_confirmed_so_restores_stock(self, auth_client, user):
        product = ProductFactory(owner=user)
        stock = StockFactory(owner=user, product=product, quantity=Decimal("100"))
        so = SalesOrderFactory(
            owner=user, product=product, stock=stock, quantity=Decimal("30")
        )
        auth_client.post(reverse("sales-order-confirm", args=[so.pk]))
        stock.refresh_from_db()
        assert stock.quantity == Decimal("70")

        resp = auth_client.post(reverse("sales-order-cancel", args=[so.pk]))
        assert resp.status_code == status.HTTP_200_OK
        stock.refresh_from_db()
        assert stock.quantity == Decimal("100")

    def test_data_isolation(self, auth_client, user):
        other = UserFactory()
        product = ProductFactory(owner=other)
        stock = StockFactory(owner=other, product=product, quantity=Decimal("50"))
        SalesOrderFactory(owner=other, product=product, stock=stock)
        resp = auth_client.get(reverse("sales-order-list"))
        assert resp.data["count"] == 0
