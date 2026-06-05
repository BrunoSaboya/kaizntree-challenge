"""
Shopify adapter — implements EcommerceAdapter for the Shopify REST Admin API.

Webhook authentication: HMAC-SHA256
  Shopify signs every webhook by computing HMAC-SHA256 over the raw request body
  using the webhook secret (Settings > Notifications > Webhooks in the Shopify admin),
  then base64-encodes the digest and sends it in the X-Shopify-Hmac-Sha256 header.

  Reference: https://shopify.dev/docs/apps/webhooks/configuration/https#step-5-verify-the-webhook

Order object shape (Shopify REST Admin API 2024-01):
  {
    "id": 820982911946154508,
    "email": "jon@doe.ca",
    "created_at": "2021-12-31T19:00:00-05:00",
    "line_items": [
      {
        "id": 866550311766439020,
        "variant_id": 808950810,
        "title": "IPod Nano - 8GB",
        "quantity": 1,
        "sku": "IPOD2008PINK",
        "price": "199.00",
        ...
      }
    ],
    "billing_address": { "name": "John Smith", ... },
    "note": "...",
    ...
  }

Inventory sync (push_inventory_update):
  Uses the Inventory Levels API: POST /admin/api/2024-01/inventory_levels/set.json
  Requires inventory_item_id (fetched via GET /variants/{variant_id}.json) and
  location_id. This is a two-step lookup that requires a credentials-aware HTTP client.
"""

import base64
import hashlib
import hmac
from datetime import datetime
from decimal import Decimal

from .base import (
    EcommerceAdapter,
    ExternalLineItem,
    ExternalOrder,
    IntegrationNotConfiguredError,
)


class ShopifyAdapter(EcommerceAdapter):
    """
    Shopify REST Admin API adapter.

    Required settings (via registry):
      SHOPIFY_WEBHOOK_SECRET  — from Shopify admin Notifications > Webhooks
      SHOPIFY_SHOP_DOMAIN     — e.g. my-store.myshopify.com
      SHOPIFY_ACCESS_TOKEN    — private app or custom app API token
    """

    def __init__(self, webhook_secret: str, shop_domain: str = "", access_token: str = ""):
        self._webhook_secret = webhook_secret
        self._shop_domain = shop_domain
        self._access_token = access_token

    @property
    def platform_name(self) -> str:
        return "Shopify"

    def validate_webhook(self, payload: bytes, signature_header: str) -> bool:
        """
        Verify X-Shopify-Hmac-Sha256 header against the raw request body.

        Never raises — returns False on any validation failure so views can
        return 401 without leaking implementation details.
        """
        if not signature_header or not self._webhook_secret:
            return False
        try:
            expected = base64.b64encode(
                hmac.new(
                    self._webhook_secret.encode("utf-8"),
                    payload,
                    hashlib.sha256,
                ).digest()
            ).decode("utf-8")
            return hmac.compare_digest(expected, signature_header)
        except Exception:
            return False

    def map_order_to_sales_order(self, raw_order: dict) -> dict:
        """
        Map a Shopify order dict to a SalesOrderSerializer-compatible payload.

        Returns one dict per line item. Caller iterates and attempts SKU → product_id
        lookup using apps.inventory.models.Product.objects.filter(owner=..., sku=...).

        Unknown SKUs are included with product_id=None so the caller can surface
        unmatched items in the UI rather than silently dropping them.
        """
        results = []
        order_date = raw_order.get("created_at", "")[:10] or str(datetime.utcnow().date())
        customer = (
            raw_order.get("billing_address", {}).get("name", "")
            or raw_order.get("email", "")
        )
        note_prefix = f"Shopify order #{raw_order.get('id', '')} — {customer}"

        for item in raw_order.get("line_items", []):
            results.append({
                "external_id": str(raw_order.get("id", "")),
                "external_sku": item.get("sku", ""),
                "external_product_name": item.get("title", ""),
                "product_id": None,  # resolved by caller via SKU lookup
                "quantity": Decimal(str(item.get("quantity", 0))),
                "price_per_unit": Decimal(str(item.get("price", "0"))),
                "order_date": order_date,
                "notes": f"{note_prefix}. Item: {item.get('title', '')}",
            })

        return {"line_items": results, "platform": "shopify", "raw": raw_order}

    def pull_orders(self, since: datetime) -> list[ExternalOrder]:
        """
        Fetch orders from GET /admin/api/2024-01/orders.json?created_at_min=...

        Real implementation:
          import requests
          resp = requests.get(
              f"https://{self._shop_domain}/admin/api/2024-01/orders.json",
              params={"created_at_min": since.isoformat(), "status": "any", "limit": 250},
              headers={"X-Shopify-Access-Token": self._access_token},
          )
          orders = resp.json()["orders"]
          return [self._to_external_order(o) for o in orders]

        Pagination: Shopify uses Link header cursor pagination for > 250 orders.
        """
        if not self._access_token:
            raise IntegrationNotConfiguredError(
                "SHOPIFY_ACCESS_TOKEN is not configured. "
                "Set it in .env to enable order polling."
            )
        raise NotImplementedError(
            "pull_orders requires a live Shopify store connection. "
            "Set SHOPIFY_SHOP_DOMAIN and SHOPIFY_ACCESS_TOKEN in .env."
        )

    def push_inventory_update(self, sku: str, qty: int) -> None:
        """
        Sync stock quantity to Shopify Inventory Levels API.

        Real implementation (two-step):
          1. GET /admin/api/2024-01/variants.json?sku={sku} → get inventory_item_id
          2. POST /admin/api/2024-01/inventory_levels/set.json
             {"location_id": ..., "inventory_item_id": ..., "available": qty}

        Requires SHOPIFY_LOCATION_ID in settings (from Shopify Admin > Locations).
        """
        if not self._access_token:
            raise IntegrationNotConfiguredError(
                "SHOPIFY_ACCESS_TOKEN is not configured."
            )
        raise NotImplementedError(
            "push_inventory_update requires live Shopify credentials."
        )

    def _to_external_order(self, raw: dict) -> ExternalOrder:
        line_items = [
            ExternalLineItem(
                external_sku=item.get("sku", ""),
                external_product_name=item.get("title", ""),
                quantity=Decimal(str(item.get("quantity", 0))),
                unit_price=Decimal(str(item.get("price", "0"))),
            )
            for item in raw.get("line_items", [])
        ]
        return ExternalOrder(
            platform="shopify",
            external_id=str(raw["id"]),
            order_date=datetime.fromisoformat(raw["created_at"][:10]).date(),
            customer_name=raw.get("billing_address", {}).get("name", ""),
            customer_email=raw.get("email", ""),
            line_items=line_items,
            notes=raw.get("note", ""),
            raw_payload=raw,
        )
