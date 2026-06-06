from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from apps.inventory.models import Stock
from apps.orders.models import OrderStatus
from apps.orders.services import (
    cancel_purchase_order,
    cancel_sales_order,
    confirm_purchase_order,
    confirm_sales_order,
)

from .factories import PurchaseOrderFactory, SalesOrderFactory
from apps.inventory.tests.factories import ProductFactory, StockFactory, UserFactory


@pytest.mark.django_db
class TestConfirmPurchaseOrder:
    def test_confirm_creates_stock(self, db):
        po = PurchaseOrderFactory(quantity=Decimal("100"))
        updated = confirm_purchase_order(po, "LOT-001")
        assert updated.status == OrderStatus.CONFIRMED
        stock = Stock.objects.get(product=po.product, identifier="LOT-001")
        assert stock.quantity == Decimal("100")

    def test_confirm_increments_existing_stock(self, db):
        product = ProductFactory()
        StockFactory(product=product, organization=product.organization, identifier="LOT-001", quantity=Decimal("50"))
        po = PurchaseOrderFactory(product=product, organization=product.organization, quantity=Decimal("100"))
        confirm_purchase_order(po, "LOT-001")
        stock = Stock.objects.get(product=product, identifier="LOT-001")
        assert stock.quantity == Decimal("150")

    def test_confirm_twice_raises(self, db):
        po = PurchaseOrderFactory()
        confirm_purchase_order(po, "LOT-001")
        po.refresh_from_db()
        with pytest.raises(ValidationError):
            confirm_purchase_order(po, "LOT-001")

    def test_cancel_draft(self, db):
        po = PurchaseOrderFactory()
        updated = cancel_purchase_order(po)
        assert updated.status == OrderStatus.CANCELLED

    def test_cancel_confirmed_raises(self, db):
        po = PurchaseOrderFactory()
        confirm_purchase_order(po, "LOT-001")
        po.refresh_from_db()
        with pytest.raises(ValidationError):
            cancel_purchase_order(po)


@pytest.mark.django_db
class TestConfirmSalesOrder:
    def test_confirm_decrements_stock(self, db):
        product = ProductFactory()
        stock = StockFactory(product=product, organization=product.organization, quantity=Decimal("100"))
        so = SalesOrderFactory(product=product, organization=product.organization, stock=stock, quantity=Decimal("30"))
        confirm_sales_order(so)
        stock.refresh_from_db()
        assert stock.quantity == Decimal("70")

    def test_confirm_insufficient_stock_raises(self, db):
        product = ProductFactory()
        stock = StockFactory(product=product, organization=product.organization, quantity=Decimal("5"))
        so = SalesOrderFactory(product=product, organization=product.organization, stock=stock, quantity=Decimal("10"))
        with pytest.raises(ValidationError, match="Insufficient"):
            confirm_sales_order(so)

    def test_confirm_twice_raises(self, db):
        product = ProductFactory()
        stock = StockFactory(product=product, organization=product.organization, quantity=Decimal("100"))
        so = SalesOrderFactory(product=product, organization=product.organization, stock=stock, quantity=Decimal("10"))
        confirm_sales_order(so)
        so.refresh_from_db()
        with pytest.raises(ValidationError):
            confirm_sales_order(so)

    def test_cancel_confirmed_restores_stock(self, db):
        product = ProductFactory()
        stock = StockFactory(product=product, organization=product.organization, quantity=Decimal("100"))
        so = SalesOrderFactory(product=product, organization=product.organization, stock=stock, quantity=Decimal("30"))
        confirm_sales_order(so)
        stock.refresh_from_db()
        assert stock.quantity == Decimal("70")

        so.refresh_from_db()
        cancel_sales_order(so)
        stock.refresh_from_db()
        assert stock.quantity == Decimal("100")

    def test_cancel_draft_does_not_touch_stock(self, db):
        product = ProductFactory()
        stock = StockFactory(product=product, organization=product.organization, quantity=Decimal("100"))
        so = SalesOrderFactory(product=product, organization=product.organization, stock=stock, quantity=Decimal("30"))
        cancel_sales_order(so)
        stock.refresh_from_db()
        assert stock.quantity == Decimal("100")

    def test_no_stock_on_draft_confirm_raises(self, db):
        product = ProductFactory()
        from apps.orders.models import SalesOrder
        import datetime
        so = SalesOrder.objects.create(
            organization=product.organization,
            product=product,
            stock=None,
            quantity=Decimal("10"),
            price_per_unit=Decimal("5"),
            order_date=datetime.date.today(),
        )
        with pytest.raises(ValidationError, match="stock"):
            confirm_sales_order(so)
