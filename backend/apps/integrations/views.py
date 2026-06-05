import json

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.models import Product
from .registry import get_shopify_adapter, get_integration_status


class IntegrationStatusView(APIView):
    """GET /api/v1/integrations/status/ — which platforms are configured."""

    def get(self, request):
        return Response(get_integration_status())


class ShopifyWebhookView(APIView):
    """
    POST /api/v1/integrations/shopify/webhook/

    Receives Shopify order/create webhooks and creates draft SalesOrders.

    Authentication: HMAC-SHA256 (X-Shopify-Hmac-Sha256 header), NOT JWT.
    This endpoint is machine-to-machine — it uses the webhook secret for
    auth and must be AllowAny at the JWT level.

    Shopify webhook topics handled:
      - orders/create  → maps to draft SalesOrder(s), one per line item

    Unmatched SKUs are skipped with a warning in the response. We never
    auto-confirm — the merchant reviews draft orders before confirming.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        adapter = get_shopify_adapter()
        if adapter is None:
            return Response(
                {"error": "Shopify integration is not configured."},
                status=503,
            )

        # Validate HMAC signature
        signature = request.headers.get("X-Shopify-Hmac-Sha256", "")
        raw_body = request.body
        if not adapter.validate_webhook(raw_body, signature):
            return Response({"error": "Invalid webhook signature."}, status=401)

        topic = request.headers.get("X-Shopify-Topic", "")
        if topic != "orders/create":
            # Accept but ignore non-order topics (Shopify also sends app/uninstalled etc.)
            return Response({"received": True, "topic": topic, "action": "ignored"})

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON payload."}, status=400)

        mapped = adapter.map_order_to_sales_order(payload)
        line_items = mapped.get("line_items", [])

        created = []
        skipped = []

        for item in line_items:
            sku = item.get("external_sku", "")
            product = None

            if sku:
                # Webhook is machine-to-machine and has no user context — we look up
                # products across all owners where the SKU matches.
                # In a multi-tenant production deployment you'd store the shop→owner
                # mapping and filter by owner instead.
                product = Product.objects.filter(sku=sku).first()

            if product is None:
                skipped.append({"sku": sku, "reason": "SKU not found in product catalog"})
                continue

            from apps.orders.models import SalesOrder, OrderStatus
            import datetime
            so = SalesOrder.objects.create(
                owner=product.owner,
                product=product,
                quantity=item["quantity"],
                price_per_unit=item["price_per_unit"],
                order_date=item.get("order_date") or str(datetime.date.today()),
                status=OrderStatus.DRAFT,
                notes=item.get("notes", ""),
            )
            created.append({"sales_order_id": so.pk, "sku": sku, "quantity": float(item["quantity"])})

        return Response({
            "received": True,
            "external_order_id": mapped.get("raw", {}).get("id", ""),
            "created_draft_orders": created,
            "skipped_items": skipped,
        })
