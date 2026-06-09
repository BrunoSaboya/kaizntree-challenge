from decimal import Decimal
from typing import Optional

from django.db.models import DecimalField, ExpressionWrapper, F, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce

from apps.inventory.models import Product, Stock
from apps.orders.models import PurchaseOrder, SalesOrder


def _round(value: Optional[Decimal], places: int = 2) -> Optional[Decimal]:
    if value is None:
        return None
    return round(value, places)


def get_financials_queryset(org):
    """
    Returns a queryset of Products annotated with financial aggregates.
    Each aggregate uses an independent correlated subquery to avoid the
    Cartesian product that occurs when joining multiple one-to-many relations
    (purchase_orders, sales_orders, stock_entries) on the same product row.
    """
    dec20_4 = DecimalField(max_digits=20, decimal_places=4)
    dec12_3 = DecimalField(max_digits=12, decimal_places=3)
    zero = Decimal("0")

    total_cost_sq = Subquery(
        PurchaseOrder.objects.filter(product_id=OuterRef("pk"), status="confirmed")
        .values("product_id")
        .annotate(val=Sum(ExpressionWrapper(F("quantity") * F("cost_per_unit"), output_field=dec20_4)))
        .values("val")[:1],
        output_field=dec20_4,
    )

    total_revenue_sq = Subquery(
        SalesOrder.objects.filter(product_id=OuterRef("pk"), status="confirmed")
        .values("product_id")
        .annotate(val=Sum(ExpressionWrapper(F("quantity") * F("price_per_unit"), output_field=dec20_4)))
        .values("val")[:1],
        output_field=dec20_4,
    )

    units_purchased_sq = Subquery(
        PurchaseOrder.objects.filter(product_id=OuterRef("pk"), status="confirmed")
        .values("product_id")
        .annotate(val=Sum("quantity"))
        .values("val")[:1],
        output_field=dec12_3,
    )

    units_sold_sq = Subquery(
        SalesOrder.objects.filter(product_id=OuterRef("pk"), status="confirmed")
        .values("product_id")
        .annotate(val=Sum("quantity"))
        .values("val")[:1],
        output_field=dec12_3,
    )

    current_stock_sq = Subquery(
        Stock.objects.filter(product_id=OuterRef("pk"))
        .values("product_id")
        .annotate(val=Sum("quantity"))
        .values("val")[:1],
        output_field=dec12_3,
    )

    return Product.objects.filter(organization=org).annotate(
        total_cost=Coalesce(total_cost_sq, zero),
        total_revenue=Coalesce(total_revenue_sq, zero),
        units_purchased=Coalesce(units_purchased_sq, zero),
        units_sold=Coalesce(units_sold_sq, zero),
        current_stock=Coalesce(current_stock_sq, zero),
    )


def _get_cogs_by_product(org) -> dict:
    """
    Compute COGS per product by tracing each confirmed SO to the cost basis of
    its stock lot: COGS = SO.quantity × lot_weighted_avg_cost.

    lot_weighted_avg_cost = sum(PO.quantity × PO.cost_per_unit) / sum(PO.quantity)
    for all confirmed POs linked to the same stock lot.
    """
    lot_avg_cost_sq = (
        PurchaseOrder.objects.filter(stock_id=OuterRef("stock_id"), status="confirmed")
        .values("stock_id")
        .annotate(
            avg=ExpressionWrapper(
                Sum(F("quantity") * F("cost_per_unit")) / Sum("quantity"),
                output_field=DecimalField(max_digits=20, decimal_places=4),
            )
        )
        .values("avg")[:1]
    )

    so_cogs_expr = ExpressionWrapper(
        F("quantity") * F("lot_avg_cost"),
        output_field=DecimalField(max_digits=20, decimal_places=4),
    )

    rows = (
        SalesOrder.objects.filter(
            product__organization=org,
            status="confirmed",
            stock__isnull=False,
        )
        .annotate(lot_avg_cost=Subquery(lot_avg_cost_sq))
        .annotate(so_cogs=so_cogs_expr)
        .values("product_id")
        .annotate(cogs=Sum("so_cogs"))
    )

    return {r["product_id"]: r["cogs"] or Decimal("0") for r in rows}


def _build_product_row(product, cogs: Decimal) -> dict:
    cost = product.total_cost or Decimal("0")
    revenue = product.total_revenue or Decimal("0")
    units_purchased = product.units_purchased or Decimal("0")
    current_stock = product.current_stock or Decimal("0")
    avg_unit_cost = cost / units_purchased if units_purchased > 0 else Decimal("0")
    inventory_value = current_stock * avg_unit_cost
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
    cogs_map = _get_cogs_by_product(org)
    return _build_product_row(product, cogs_map.get(product_id, Decimal("0")))


def get_all_product_financials(org) -> list[dict]:
    cogs_map = _get_cogs_by_product(org)
    return [
        _build_product_row(p, cogs_map.get(p.pk, Decimal("0")))
        for p in get_financials_queryset(org)
    ]


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
