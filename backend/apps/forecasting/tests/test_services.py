import math
from datetime import date, timedelta
from decimal import Decimal

import pytest
from freezegun import freeze_time

from apps.inventory.models import MovementType, StockMovement
from apps.inventory.tests.factories import ProductFactory, StockFactory, UserFactory
from apps.orders.tests.factories import PurchaseOrderFactory, SalesOrderFactory
from apps.orders.services import confirm_purchase_order, confirm_sales_order
from apps.forecasting.services import (
    _daily_consumption_series,
    get_reorder_recommendations,
)


@pytest.mark.django_db
class TestDailyConsumptionSeries:
    def test_no_movements_returns_zeros(self):
        user = UserFactory()
        product = ProductFactory(owner=user)
        series = _daily_consumption_series(product.pk, user, 30)
        assert len(series) == 30
        assert all(v == 0.0 for v in series)

    def test_single_sale_day_appears_in_series(self):
        user = UserFactory()
        product = ProductFactory(owner=user)
        stock = StockFactory(owner=user, product=product, quantity=Decimal("100"))

        today = date.today()
        with freeze_time(today - timedelta(days=5)):
            so = SalesOrderFactory(
                owner=user, product=product, stock=stock,
                quantity=Decimal("10"), order_date=today - timedelta(days=5),
            )
            confirm_sales_order(so)

        series = _daily_consumption_series(product.pk, user, 30)
        assert len(series) == 30
        assert sum(series) == pytest.approx(10.0, abs=0.001)

    def test_multiple_sales_accumulate_correctly(self):
        user = UserFactory()
        product = ProductFactory(owner=user)
        stock = StockFactory(owner=user, product=product, quantity=Decimal("500"))

        for days_ago in [1, 2, 3]:
            d = date.today() - timedelta(days=days_ago)
            with freeze_time(d):
                so = SalesOrderFactory(
                    owner=user, product=product, stock=stock,
                    quantity=Decimal("20"), order_date=d,
                )
                confirm_sales_order(so)

        series = _daily_consumption_series(product.pk, user, 30)
        assert sum(series) == pytest.approx(60.0, abs=0.001)

    def test_purchase_movements_excluded(self):
        user = UserFactory()
        product = ProductFactory(owner=user)
        po = PurchaseOrderFactory(owner=user, product=product, quantity=Decimal("50"))
        confirm_purchase_order(po, "LOT-TEST")

        series = _daily_consumption_series(product.pk, user, 30)
        assert sum(series) == 0.0


@pytest.mark.django_db
class TestReorderRecommendations:
    def test_empty_returns_all_products(self):
        user = UserFactory()
        ProductFactory(owner=user, name="A")
        ProductFactory(owner=user, name="B")
        results = get_reorder_recommendations(user)
        assert len(results) == 2

    def test_out_of_stock_status(self):
        user = UserFactory()
        product = ProductFactory(owner=user, min_stock_quantity=10)
        results = get_reorder_recommendations(user)
        assert results[0]["status"] == "OUT_OF_STOCK"
        assert results[0]["current_stock"] == 0.0

    def test_ok_status_with_ample_stock(self):
        user = UserFactory()
        product = ProductFactory(owner=user)
        StockFactory(owner=user, product=product, quantity=Decimal("1000"))
        results = get_reorder_recommendations(user)
        assert results[0]["status"] == "OK"
        assert results[0]["current_stock"] == pytest.approx(1000.0, abs=0.001)

    def test_response_shape(self):
        user = UserFactory()
        ProductFactory(owner=user)
        results = get_reorder_recommendations(user)
        row = results[0]
        required_keys = {
            "product_id", "product_name", "sku", "unit_type",
            "current_stock", "avg_daily_consumption", "sigma_daily",
            "safety_stock", "reorder_point", "days_of_stock_remaining",
            "recommended_reorder_qty", "lead_time_days", "status",
        }
        assert required_keys.issubset(row.keys())

    def test_safety_stock_formula(self):
        """safety_stock = 1.65 * sigma * sqrt(lead_time). With zero variance, safety_stock = 0."""
        user = UserFactory()
        product = ProductFactory(owner=user)
        StockFactory(owner=user, product=product, quantity=Decimal("500"))
        results = get_reorder_recommendations(user)
        row = results[0]
        assert row["safety_stock"] == pytest.approx(0.0, abs=0.01)

    def test_data_isolation(self):
        user1 = UserFactory()
        user2 = UserFactory()
        ProductFactory(owner=user1)
        ProductFactory(owner=user2)
        results = get_reorder_recommendations(user1)
        assert len(results) == 1

    def test_days_of_stock_none_when_no_consumption(self):
        user = UserFactory()
        product = ProductFactory(owner=user)
        StockFactory(owner=user, product=product, quantity=Decimal("100"))
        results = get_reorder_recommendations(user)
        assert results[0]["days_of_stock_remaining"] is None
        assert results[0]["avg_daily_consumption"] == 0.0
