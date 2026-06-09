from decimal import Decimal

import pytest

from apps.financials.services import get_all_product_financials, get_summary
from apps.inventory.tests.factories import OrganizationFactory, ProductFactory, StockFactory, UserFactory
from apps.orders.models import OrderStatus
from apps.orders.tests.factories import PurchaseOrderFactory, SalesOrderFactory


def make_confirmed_po(product, quantity, cost_per_unit):
    po = PurchaseOrderFactory(
        product=product,
        organization=product.organization,
        quantity=quantity,
        cost_per_unit=cost_per_unit,
    )
    from apps.orders.services import confirm_purchase_order
    return confirm_purchase_order(po, f"LOT-{po.pk}")


def make_confirmed_so(product, stock, quantity, price_per_unit):
    so = SalesOrderFactory(
        product=product,
        organization=product.organization,
        stock=stock,
        quantity=quantity,
        price_per_unit=price_per_unit,
    )
    from apps.orders.services import confirm_sales_order
    confirm_sales_order(so)
    return so


@pytest.mark.django_db
class TestFinancialCalculations:
    def test_profit_and_margin(self, db):
        """100 units @ $1 cost, 90 sold @ $10 → cogs=$90, profit=$810, margin=90%"""
        product = ProductFactory()
        po = make_confirmed_po(product, Decimal("100"), Decimal("1.0000"))
        stock = po.stock
        make_confirmed_so(product, stock, Decimal("90"), Decimal("10.0000"))

        rows = get_all_product_financials(product.organization)
        assert len(rows) == 1
        row = rows[0]
        assert row["total_cost"] == Decimal("100.00")
        assert row["cogs"] == Decimal("90.00")    # 90 sold × $1 avg cost
        assert row["total_revenue"] == Decimal("900.00")
        assert row["profit"] == Decimal("810.00")
        assert row["margin_pct"] == Decimal("90.00")

    def test_zero_sales(self, db):
        """No sales → COGS=0 (all purchased units remain in stock), profit=0"""
        product = ProductFactory()
        make_confirmed_po(product, Decimal("50"), Decimal("2.0000"))
        rows = get_all_product_financials(product.organization)
        row = rows[0]
        assert row["total_cost"] == Decimal("100.00")
        assert row["cogs"] == Decimal("0.00")
        assert row["total_revenue"] == Decimal("0.00")
        assert row["profit"] == Decimal("0.00")

    def test_zero_cost_margin_is_none(self, db):
        product = ProductFactory()
        rows = get_all_product_financials(product.organization)
        row = rows[0]
        assert row["margin_pct"] is None

    def test_draft_orders_excluded(self, db):
        product = ProductFactory()
        PurchaseOrderFactory(
            product=product,
            organization=product.organization,
            status=OrderStatus.DRAFT,
        )
        rows = get_all_product_financials(product.organization)
        row = rows[0]
        assert row["total_cost"] == Decimal("0.00")

    def test_summary_aggregates_multiple_products(self, db):
        org = OrganizationFactory()
        p1 = ProductFactory(organization=org)
        p2 = ProductFactory(organization=org)

        po1 = make_confirmed_po(p1, Decimal("100"), Decimal("1.0000"))
        make_confirmed_so(p1, po1.stock, Decimal("100"), Decimal("2.0000"))

        po2 = make_confirmed_po(p2, Decimal("50"), Decimal("4.0000"))
        make_confirmed_so(p2, po2.stock, Decimal("50"), Decimal("8.0000"))

        summary = get_summary(org)
        assert summary["total_cost"] == Decimal("300.00")    # 100 + 200 (procurement cost)
        assert summary["total_cogs"] == Decimal("300.00")    # all units sold, so COGS = total_cost
        assert summary["total_revenue"] == Decimal("600.00")  # 200 + 400
        assert summary["total_profit"] == Decimal("300.00")
        assert summary["product_count"] == 2

    def test_multi_lot_cogs(self, db):
        """COGS traced per lot: sells from different lots with different costs."""
        product = ProductFactory()
        po1 = make_confirmed_po(product, Decimal("50"), Decimal("2.0000"))   # LOT-A @ $2
        po2 = make_confirmed_po(product, Decimal("100"), Decimal("3.0000"))  # LOT-B @ $3
        make_confirmed_so(product, po1.stock, Decimal("20"), Decimal("5.0000"))  # 20 from LOT-A
        make_confirmed_so(product, po2.stock, Decimal("30"), Decimal("5.0000"))  # 30 from LOT-B

        rows = get_all_product_financials(product.organization)
        row = rows[0]
        assert row["total_cost"] == Decimal("400.00")   # 50×$2 + 100×$3
        assert row["total_revenue"] == Decimal("250.00")  # 20×$5 + 30×$5
        # lot-level COGS: 20×$2 + 30×$3 = $40 + $90 = $130
        # (product-level avg would give $400/150 × 50 ≈ $133.33 — different)
        assert row["cogs"] == Decimal("130.00")
        assert row["profit"] == Decimal("120.00")  # $250 - $130

    def test_data_isolation(self, db):
        org1 = OrganizationFactory()
        org2 = OrganizationFactory()
        p1 = ProductFactory(organization=org1)
        p2 = ProductFactory(organization=org2)
        make_confirmed_po(p1, Decimal("100"), Decimal("1"))
        make_confirmed_po(p2, Decimal("999"), Decimal("999"))

        rows = get_all_product_financials(org1)
        assert len(rows) == 1
        assert rows[0]["product_id"] == p1.pk
