from decimal import Decimal
from typing import Optional

from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum

from apps.inventory.models import Product, Stock


def _round(value: Optional[Decimal], places: int = 2) -> Optional[Decimal]:
    if value is None:
        return None
    return round(value, places)


def get_financials_queryset(org):
    """
    Returns a queryset of Products annotated with financial aggregates.
    All aggregation happens in a single DB query.
    """
    cost_expr = ExpressionWrapper(
        F("purchase_orders__quantity") * F("purchase_orders__cost_per_unit"),
        output_field=DecimalField(max_digits=20, decimal_places=4),
    )
    revenue_expr = ExpressionWrapper(
        F("sales_orders__quantity") * F("sales_orders__price_per_unit"),
        output_field=DecimalField(max_digits=20, decimal_places=4),
    )

    return (
        Product.objects.filter(organization=org)
        .annotate(
            total_cost=Sum(cost_expr, filter=Q(purchase_orders__status="confirmed"), default=Decimal("0")),
            total_revenue=Sum(revenue_expr, filter=Q(sales_orders__status="confirmed"), default=Decimal("0")),
            units_purchased=Sum(
                "purchase_orders__quantity",
                filter=Q(purchase_orders__status="confirmed"),
                default=Decimal("0"),
            ),
            units_sold=Sum(
                "sales_orders__quantity",
                filter=Q(sales_orders__status="confirmed"),
                default=Decimal("0"),
            ),
            current_stock=Sum("stock_entries__quantity", default=Decimal("0")),
        )
    )


def _build_product_row(product) -> dict:
    cost = product.total_cost or Decimal("0")
    revenue = product.total_revenue or Decimal("0")
    units_purchased = product.units_purchased or Decimal("0")
    current_stock = product.current_stock or Decimal("0")
    avg_unit_cost = cost / units_purchased if units_purchased > 0 else Decimal("0")
    inventory_value = current_stock * avg_unit_cost
    cogs = cost - inventory_value
    profit = revenue - cogs
    margin_pct = (profit / revenue * 100) if revenue > 0 else None

    return {
        "product_id": product.pk,
        "product_name": product.name,
        "sku": product.sku,
        "unit_type": product.unit_type,
        "min_stock_quantity": product.min_stock_quantity,
        "total_cost": _round(cost),
        "cogs": _round(cogs),
        "total_revenue": _round(revenue),
        "profit": _round(profit),
        "margin_pct": _round(margin_pct),
        "units_purchased": _round(units_purchased, 3),
        "units_sold": _round(product.units_sold, 3),
        "current_stock": _round(current_stock, 3),
        "inventory_value": _round(inventory_value),
    }


def get_product_financials(org, product_id: int) -> dict:
    qs = get_financials_queryset(org).filter(pk=product_id)
    product = qs.first()
    if product is None:
        return {}
    return _build_product_row(product)


def get_all_product_financials(org) -> list[dict]:
    return [_build_product_row(p) for p in get_financials_queryset(org)]


def get_summary(org) -> dict:
    rows = get_all_product_financials(org)
    zero = Decimal("0")
    total_cost = sum((r["total_cost"] or zero for r in rows), zero)
    total_cogs = sum((r["cogs"] or zero for r in rows), zero)
    total_revenue = sum((r["total_revenue"] or zero for r in rows), zero)
    total_profit = total_revenue - total_cogs
    overall_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else None

    total_inventory_value = sum((r["inventory_value"] or zero for r in rows), zero)

    return {
        "total_cost": _round(total_cost),
        "total_cogs": _round(total_cogs),
        "total_revenue": _round(total_revenue),
        "total_profit": _round(total_profit),
        "overall_margin_pct": _round(overall_margin),
        "inventory_value": _round(total_inventory_value),
        "product_count": len(rows),
    }
