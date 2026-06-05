"""
CPG demand forecasting — reorder point and safety stock calculations.

Algorithm:
  avg_daily_consumption = sum of outbound movements in last 30 days / 30
  sigma_daily           = population std dev of daily consumption
  safety_stock          = 1.65 * sigma_daily * sqrt(lead_time_days)  [95% service level]
  reorder_point         = avg_daily_consumption * lead_time_days + safety_stock
  days_of_stock         = current_stock / avg_daily_consumption  (None if no consumption)
  reorder_qty           = max(avg_daily_consumption * lead_time_days * 2, min_stock_quantity)
"""

import math
import statistics
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum

from apps.inventory.models import MovementType, StockMovement
from apps.inventory.models import Product


_LOOKBACK_DAYS = 30
_Z_95 = 1.65  # 95% service level z-score


def _daily_consumption_series(product_id: int, owner, lookback_days: int) -> list[float]:
    """Returns a list of daily consumption quantities (outbound only) over the lookback window."""
    cutoff = date.today() - timedelta(days=lookback_days)
    movements = (
        StockMovement.objects.filter(
            owner=owner,
            product_id=product_id,
            movement_type=MovementType.SALES_CONFIRMED,
            created_at__date__gte=cutoff,
        )
        .values("created_at__date")
        .annotate(daily_qty=Sum("quantity_change"))
        .order_by("created_at__date")
    )

    daily_map: dict[date, float] = {}
    for row in movements:
        daily_map[row["created_at__date"]] = abs(float(row["daily_qty"]))

    series = []
    for i in range(lookback_days):
        d = cutoff + timedelta(days=i)
        series.append(daily_map.get(d, 0.0))
    return series


def _current_stock(product_id: int, owner) -> Decimal:
    result = (
        Product.objects.filter(pk=product_id, owner=owner)
        .annotate(total=Sum("stock_entries__quantity"))
        .values_list("total", flat=True)
        .first()
    )
    return result or Decimal("0")


def _reorder_status(days_of_stock, reorder_point, current_stock_val, avg_daily) -> str:
    if current_stock_val <= 0:
        return "OUT_OF_STOCK"
    if avg_daily == 0:
        return "OK"
    if days_of_stock is not None and days_of_stock <= reorder_point / max(avg_daily, 0.001):
        return "CRITICAL" if days_of_stock <= 3 else "LOW"
    return "OK"


def get_reorder_recommendations(user) -> list[dict]:
    from apps.suppliers.models import Supplier

    supplier_lead_times: dict[int, int] = {}
    for s in Supplier.objects.filter(owner=user, active=True).values("id", "lead_time_days"):
        supplier_lead_times[s["id"]] = s["lead_time_days"]

    from apps.orders.models import PurchaseOrder
    product_supplier_lead: dict[int, int] = {}
    for po in (
        PurchaseOrder.objects.filter(owner=user, supplier__isnull=False)
        .values("product_id", "supplier__lead_time_days")
        .order_by("product_id", "-order_date")
        .distinct("product_id")
    ):
        product_supplier_lead[po["product_id"]] = po["supplier__lead_time_days"] or 7

    products = Product.objects.filter(owner=user).order_by("name")
    results = []

    for product in products:
        lead_time_days = product_supplier_lead.get(product.pk, 7)
        series = _daily_consumption_series(product.pk, user, _LOOKBACK_DAYS)
        avg_daily = sum(series) / len(series) if series else 0.0

        try:
            sigma = statistics.pstdev(series)
        except statistics.StatisticsError:
            sigma = 0.0

        safety_stock = _Z_95 * sigma * math.sqrt(max(lead_time_days, 1))
        reorder_point = avg_daily * lead_time_days + safety_stock

        current = float(_current_stock(product.pk, user))
        days_of_stock = (current / avg_daily) if avg_daily > 0 else None

        recommended_reorder_qty = max(
            avg_daily * lead_time_days * 2,
            float(product.min_stock_quantity),
        ) if avg_daily > 0 else float(product.min_stock_quantity)

        status = "OK"
        if current <= 0:
            status = "OUT_OF_STOCK"
        elif avg_daily > 0 and days_of_stock is not None:
            if days_of_stock <= 3:
                status = "CRITICAL"
            elif current <= reorder_point:
                status = "LOW"

        results.append({
            "product_id": product.pk,
            "product_name": product.name,
            "sku": product.sku,
            "unit_type": product.unit_type,
            "current_stock": round(current, 3),
            "avg_daily_consumption": round(avg_daily, 3),
            "sigma_daily": round(sigma, 3),
            "safety_stock": round(safety_stock, 3),
            "reorder_point": round(reorder_point, 3),
            "days_of_stock_remaining": round(days_of_stock, 1) if days_of_stock is not None else None,
            "recommended_reorder_qty": round(recommended_reorder_qty, 3),
            "lead_time_days": lead_time_days,
            "status": status,
        })

    return results
