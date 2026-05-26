from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.inventory.models import Stock

from .models import OrderStatus, PurchaseOrder, SalesOrder


def confirm_purchase_order(po: PurchaseOrder, stock_identifier: str) -> PurchaseOrder:
    if po.status != OrderStatus.DRAFT:
        raise ValidationError(f"Only draft orders can be confirmed. Current status: {po.status}.")

    with transaction.atomic():
        po_locked = PurchaseOrder.objects.select_for_update().get(pk=po.pk)
        if po_locked.status != OrderStatus.DRAFT:
            raise ValidationError("Order was already processed by another request.")

        stock, _ = Stock.objects.get_or_create(
            owner=po.owner,
            product=po.product,
            identifier=stock_identifier,
            defaults={"quantity": Decimal("0")},
        )
        Stock.objects.filter(pk=stock.pk).update(
            quantity=stock.quantity + po.quantity
        )
        stock.refresh_from_db()

        po_locked.status = OrderStatus.CONFIRMED
        po_locked.stock = stock
        po_locked.save(update_fields=["status", "stock", "updated_at"])

    return PurchaseOrder.objects.select_related("product", "stock").get(pk=po.pk)


def cancel_purchase_order(po: PurchaseOrder) -> PurchaseOrder:
    if po.status == OrderStatus.CANCELLED:
        raise ValidationError("Order is already cancelled.")
    if po.status == OrderStatus.CONFIRMED:
        raise ValidationError("Confirmed purchase orders cannot be cancelled. Contact support.")

    with transaction.atomic():
        po.status = OrderStatus.CANCELLED
        po.save(update_fields=["status", "updated_at"])

    return po


def confirm_sales_order(so: SalesOrder) -> SalesOrder:
    if so.status != OrderStatus.DRAFT:
        raise ValidationError(f"Only draft orders can be confirmed. Current status: {so.status}.")
    if not so.stock_id:
        raise ValidationError("A stock entry must be selected before confirming.")

    with transaction.atomic():
        so_locked = SalesOrder.objects.select_for_update().get(pk=so.pk)
        if so_locked.status != OrderStatus.DRAFT:
            raise ValidationError("Order was already processed by another request.")

        stock = Stock.objects.select_for_update().get(pk=so.stock_id)
        if stock.quantity < so.quantity:
            raise ValidationError(
                f"Insufficient stock. Available: {stock.quantity}, required: {so.quantity}."
            )

        Stock.objects.filter(pk=stock.pk).update(
            quantity=stock.quantity - so.quantity
        )

        so_locked.status = OrderStatus.CONFIRMED
        so_locked.save(update_fields=["status", "updated_at"])

    return SalesOrder.objects.select_related("product", "stock").get(pk=so.pk)


def cancel_sales_order(so: SalesOrder) -> SalesOrder:
    if so.status == OrderStatus.CANCELLED:
        raise ValidationError("Order is already cancelled.")

    with transaction.atomic():
        if so.status == OrderStatus.CONFIRMED and so.stock_id:
            Stock.objects.filter(pk=so.stock_id).update(
                quantity=Stock.objects.get(pk=so.stock_id).quantity + so.quantity
            )

        so.status = OrderStatus.CANCELLED
        so.save(update_fields=["status", "updated_at"])

    return so
