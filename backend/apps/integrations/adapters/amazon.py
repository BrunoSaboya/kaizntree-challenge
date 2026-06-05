"""
Amazon SP-API adapter — implements EcommerceAdapter for Amazon Selling Partner API.

Authentication: SP-API uses LWA (Login with Amazon) OAuth2 + AWS SigV4.
  Unlike the legacy MWS (Marketplace Web Service), SP-API requires:
  1. LWA refresh token (from Seller Central > Apps & Services > Develop Apps)
  2. AWS IAM role ARN with AmazonSellerPartnerAPIExecutionPolicy
  3. AWS access key / secret for signing requests

Webhook (Notifications) authentication:
  Amazon SP-API delivers notifications via AWS SNS. Each SNS message includes
  a Signature field — RSA-SHA1 signed over a canonical string of SNS message fields.
  Verification requires fetching the SigningCertURL and checking it against
  Amazon's SNS certificate domains (sns.amazonaws.com).

  Reference: https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature.html

Order object shape (SP-API GetOrders response, 2024-01):
  {
    "AmazonOrderId": "902-3159896-1390916",
    "PurchaseDate": "2024-01-15T18:04:00Z",
    "OrderStatus": "Unshipped",
    "OrderItems": [
      {
        "ASIN": "B00000J1ER",
        "SellerSKU": "OATS-001",
        "OrderItemId": "68828574383266",
        "Title": "Organic Oats 1kg",
        "QuantityOrdered": 2,
        "ItemPrice": {"Amount": "19.98", "CurrencyCode": "USD"},
        ...
      }
    ],
    "BuyerInfo": {"BuyerEmail": "buyer@example.com"},
    ...
  }

ASIN vs SKU:
  Amazon orders carry both ASIN (Amazon-native) and SellerSKU (merchant-set).
  Kaizntree matches on SellerSKU = Product.sku for the same reason Shopify does —
  the merchant controls SKUs in both systems.
"""

from datetime import datetime
from decimal import Decimal

from .base import (
    EcommerceAdapter,
    ExternalLineItem,
    ExternalOrder,
    IntegrationNotConfiguredError,
)


class AmazonAdapter(EcommerceAdapter):
    """
    Amazon Selling Partner API (SP-API) adapter.

    Required settings (via registry):
      AMAZON_SELLER_ID        — Merchant Token from Seller Central
      AMAZON_LWA_CLIENT_ID    — LWA application client ID
      AMAZON_LWA_CLIENT_SECRET
      AMAZON_LWA_REFRESH_TOKEN — per-seller OAuth refresh token
      AMAZON_AWS_ACCESS_KEY   — IAM user access key with SP-API execution role
      AMAZON_AWS_SECRET_KEY
      AMAZON_AWS_REGION       — e.g. us-east-1
      AMAZON_MARKETPLACE_ID   — e.g. ATVPDKIKX0DER (US)
    """

    def __init__(self, seller_id: str, **credentials):
        self._seller_id = seller_id
        self._credentials = credentials

    @property
    def platform_name(self) -> str:
        return "Amazon"

    def validate_webhook(self, payload: bytes, signature_header: str) -> bool:
        """
        Verify SNS message signature (RSA-SHA1).

        Real implementation:
          1. Parse the SNS JSON body to get SigningCertURL + Signature + fields
          2. Verify SigningCertURL domain matches *.sns.*.amazonaws.com
          3. Download cert, extract public key
          4. Build canonical string from Type, MessageId, Timestamp, TopicArn, Message
          5. RSA verify base64-decoded Signature against canonical string using SHA1

        Using the aws_sns_message_validator PyPI package is the standard approach.
        """
        if not self._seller_id:
            return False
        # Full SNS signature validation requires fetching the cert URL (network call).
        # In production, use: pip install aws-sns-message-validator
        raise NotImplementedError(
            "Amazon SNS webhook validation requires network access to fetch "
            "the signing certificate. Use aws_sns_message_validator in production."
        )

    def map_order_to_sales_order(self, raw_order: dict) -> dict:
        """
        Map an SP-API order dict (including OrderItems) to a SalesOrderSerializer payload.

        SP-API quirk: OrderItems are fetched via a separate GetOrderItems call —
        they are not nested in the GetOrders response. This method expects the
        caller to have already merged order + items into raw_order["OrderItems"].
        """
        results = []
        order_date = raw_order.get("PurchaseDate", "")[:10] or str(datetime.utcnow().date())
        amazon_order_id = raw_order.get("AmazonOrderId", "")
        buyer_email = raw_order.get("BuyerInfo", {}).get("BuyerEmail", "")

        for item in raw_order.get("OrderItems", []):
            item_price = item.get("ItemPrice", {})
            unit_price = Decimal("0")
            qty = Decimal(str(item.get("QuantityOrdered", 0)))
            if qty and item_price.get("Amount"):
                unit_price = Decimal(str(item_price["Amount"])) / qty

            results.append({
                "external_id": amazon_order_id,
                "external_sku": item.get("SellerSKU", ""),
                "external_product_name": item.get("Title", ""),
                "external_asin": item.get("ASIN", ""),
                "product_id": None,  # resolved by caller via SellerSKU → Product.sku lookup
                "quantity": qty,
                "price_per_unit": unit_price,
                "order_date": order_date,
                "notes": f"Amazon order {amazon_order_id} — buyer: {buyer_email}",
            })

        return {"line_items": results, "platform": "amazon", "raw": raw_order}

    def pull_orders(self, since: datetime) -> list[ExternalOrder]:
        """
        Fetch orders via SP-API GET /orders/v0/orders?CreatedAfter=...

        Real implementation requires sp-api PyPI package or manual LWA + SigV4:
          from sp_api.api import Orders
          from sp_api.base import Marketplaces
          orders_api = Orders(credentials=self._credentials, marketplace=Marketplaces.US)
          response = orders_api.get_orders(CreatedAfter=since.isoformat())

        Pagination: SP-API uses NextToken in the response for > 100 orders.
        """
        if not self._seller_id:
            raise IntegrationNotConfiguredError(
                "AMAZON_SELLER_ID is not configured. "
                "Set SP-API credentials in .env to enable order polling."
            )
        raise NotImplementedError(
            "pull_orders requires live Amazon SP-API credentials."
        )

    def push_inventory_update(self, sku: str, qty: int) -> None:
        """
        Update FBA/FBM inventory quantity via SP-API Inventory API.

        For FBM (Fulfilled by Merchant): PATCH /listings/2021-08-01/items/{sellerId}/{sku}
          with fulfillmentAvailability[].quantity

        For FBA: Amazon controls FBA quantity based on shipments — direct qty
        updates are not supported. Signal a reorder instead.
        """
        if not self._seller_id:
            raise IntegrationNotConfiguredError("AMAZON_SELLER_ID is not configured.")
        raise NotImplementedError(
            "push_inventory_update requires live Amazon SP-API credentials."
        )
