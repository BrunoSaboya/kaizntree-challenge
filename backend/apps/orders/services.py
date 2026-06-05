from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.inventory.models import MovementType, Stock, StockMovement

from .models import OrderStatus, PurchaseOrder, SalesOrder


def _record_movement(owner, stock, movement_type, quantity_change, reference_type, reference_id, notes=""):
    StockMovement.objects.create(
        owner=owner,
        stock=stock,
        product=stock.product,
        movement_type=movement_type,
        quantity_change=quantity_change,
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
    )


def confirm_purchase_order(
    po: PurchaseOrder,
    stock_identifier: str,
    expiry_date=None,
    stock_notes: str = "",
) -> PurchaseOrder:
    if po.status != OrderStatus.DRAFT:
        raise ValidationError(f"Only draft orders can be confirmed. Current status: {po.status}.")

    with transaction.atomic():
        po_locked = PurchaseOrder.objects.select_for_update().get(pk=po.pk)
        if po_locked.status != OrderStatus.DRAFT:
            raise ValidationError("Order was already processed by another request.")

        defaults = {"quantity": Decimal("0")}
        if expiry_date is not None:
            defaults["expiry_date"] = expiry_date
        if stock_notes:
            defaults["notes"] = stock_notes

        stock, _ = Stock.objects.get_or_create(
            owner=po.owner,
            product=po.product,
            identifier=stock_identifier,
            defaults=defaults,
        )
        Stock.objects.filter(pk=stock.pk).update(
            quantity=stock.quantity + po.quantity
        )
        stock.refresh_from_db()

        _record_movement(
            owner=po.owner,
            stock=stock,
            movement_type=MovementType.PURCHASE_CONFIRMED,
            quantity_change=po.quantity,
            reference_type="purchase_order",
            reference_id=po.pk,
        )

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

        _record_movement(
            owner=so.owner,
            stock=stock,
            movement_type=MovementType.SALES_CONFIRMED,
            quantity_change=-so.quantity,
            reference_type="sales_order",
            reference_id=so.pk,
        )

        so_locked.status = OrderStatus.CONFIRMED
        so_locked.save(update_fields=["status", "updated_at"])

    return SalesOrder.objects.select_related("product", "stock").get(pk=so.pk)


def cancel_sales_order(so: SalesOrder) -> SalesOrder:
    if so.status == OrderStatus.CANCELLED:
        raise ValidationError("Order is already cancelled.")

    with transaction.atomic():
        if so.status == OrderStatus.CONFIRMED and so.stock_id:
            stock = Stock.objects.get(pk=so.stock_id)
            Stock.objects.filter(pk=so.stock_id).update(
                quantity=stock.quantity + so.quantity
            )
            _record_movement(
                owner=so.owner,
                stock=stock,
                movement_type=MovementType.SALES_CANCELLED,
                quantity_change=so.quantity,
                reference_type="sales_order",
                reference_id=so.pk,
            )

        so.status = OrderStatus.CANCELLED
        so.save(update_fields=["status", "updated_at"])

    return so
