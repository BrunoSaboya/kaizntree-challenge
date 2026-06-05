"""
Integration adapter tests.

Key tests:
- Shopify HMAC validation (real cryptographic logic, no mocks)
- Shopify order → SalesOrder dict mapping (real field mapping)
- QuickBooks PO → Bill mapping (real field mapping)
- NetSuite Supplier → Vendor mapping (real field mapping)
- Registry returns None when credentials absent (graceful degradation)
"""

import base64
import hashlib
import hmac
import json
from decimal import Decimal

import pytest

from apps.integrations.adapters.shopify import ShopifyAdapter
from apps.integrations.adapters.quickbooks import QuickBooksAdapter
from apps.integrations.adapters.netsuite import NetSuiteAdapter
from apps.integrations.adapters.base import IntegrationNotConfiguredError
from apps.integrations.registry import (
    get_shopify_adapter,
    get_quickbooks_adapter,
    get_netsuite_adapter,
    get_integration_status,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hmac(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


# ---------------------------------------------------------------------------
# Shopify HMAC validation
# ---------------------------------------------------------------------------

class TestShopifyWebhookValidation:
    def test_valid_signature(self):
        secret = "test_webhook_secret"
        body = b'{"id": 123, "line_items": []}'
        adapter = ShopifyAdapter(webhook_secret=secret)

        sig = _make_hmac(secret, body)
        assert adapter.validate_webhook(body, sig) is True

    def test_invalid_signature_returns_false(self):
        adapter = ShopifyAdapter(webhook_secret="real_secret")
        body = b'{"id": 123}'
        wrong_sig = _make_hmac("wrong_secret", body)
        assert adapter.validate_webhook(body, wrong_sig) is False

    def test_empty_signature_returns_false(self):
        adapter = ShopifyAdapter(webhook_secret="secret")
        assert adapter.validate_webhook(b'{"id": 1}', "") is False

    def test_empty_secret_returns_false(self):
        adapter = ShopifyAdapter(webhook_secret="")
        body = b'{"id": 1}'
        # Even if someone computes a valid HMAC with empty key, we reject it
        assert adapter.validate_webhook(body, _make_hmac("", body)) is False

    def test_tampered_body_returns_false(self):
        secret = "secret123"
        original_body = b'{"id": 123, "total_price": "99.00"}'
        tampered_body = b'{"id": 123, "total_price": "1.00"}'  # price tampered
        sig = _make_hmac(secret, original_body)
        adapter = ShopifyAdapter(webhook_secret=secret)
        assert adapter.validate_webhook(tampered_body, sig) is False


# ---------------------------------------------------------------------------
# Shopify order → SalesOrder mapping
# ---------------------------------------------------------------------------

SHOPIFY_ORDER_FIXTURE = {
    "id": 820982911946154508,
    "email": "buyer@example.com",
    "created_at": "2024-01-15T10:30:00-05:00",
    "note": "Please handle carefully",
    "line_items": [
        {
            "id": 866550311766439020,
            "title": "Organic Oats 1kg",
            "quantity": 2,
            "sku": "OAT-001",
            "price": "9.99",
        },
        {
            "id": 141249953214522978,
            "title": "Hemp Seeds 500g",
            "quantity": 5,
            "sku": "HEMP-500",
            "price": "14.50",
        },
    ],
    "billing_address": {"name": "Jane Smith", "address1": "123 Main St"},
}


class TestShopifyOrderMapping:
    def setup_method(self):
        self.adapter = ShopifyAdapter(webhook_secret="secret")

    def test_maps_correct_number_of_line_items(self):
        result = self.adapter.map_order_to_sales_order(SHOPIFY_ORDER_FIXTURE)
        assert len(result["line_items"]) == 2

    def test_maps_sku_correctly(self):
        result = self.adapter.map_order_to_sales_order(SHOPIFY_ORDER_FIXTURE)
        skus = [item["external_sku"] for item in result["line_items"]]
        assert "OAT-001" in skus
        assert "HEMP-500" in skus

    def test_maps_quantity_as_decimal(self):
        result = self.adapter.map_order_to_sales_order(SHOPIFY_ORDER_FIXTURE)
        oats = next(i for i in result["line_items"] if i["external_sku"] == "OAT-001")
        assert oats["quantity"] == Decimal("2")

    def test_maps_price_as_decimal(self):
        result = self.adapter.map_order_to_sales_order(SHOPIFY_ORDER_FIXTURE)
        oats = next(i for i in result["line_items"] if i["external_sku"] == "OAT-001")
        assert oats["price_per_unit"] == Decimal("9.99")

    def test_product_id_is_none_before_lookup(self):
        result = self.adapter.map_order_to_sales_order(SHOPIFY_ORDER_FIXTURE)
        for item in result["line_items"]:
            assert item["product_id"] is None

    def test_order_date_extracted(self):
        result = self.adapter.map_order_to_sales_order(SHOPIFY_ORDER_FIXTURE)
        assert result["line_items"][0]["order_date"] == "2024-01-15"

    def test_platform_label(self):
        result = self.adapter.map_order_to_sales_order(SHOPIFY_ORDER_FIXTURE)
        assert result["platform"] == "shopify"

    def test_empty_line_items(self):
        result = self.adapter.map_order_to_sales_order({**SHOPIFY_ORDER_FIXTURE, "line_items": []})
        assert result["line_items"] == []

    def test_pull_orders_raises_without_token(self):
        from datetime import datetime
        adapter = ShopifyAdapter(webhook_secret="secret")  # no access_token
        with pytest.raises(IntegrationNotConfiguredError):
            adapter.pull_orders(since=datetime.utcnow())


# ---------------------------------------------------------------------------
# QuickBooks PO → Bill mapping
# ---------------------------------------------------------------------------

class TestQuickBooksMapping:
    def setup_method(self):
        self.adapter = QuickBooksAdapter(
            client_id="test_client_id",
            realm_id="1234567890",
            environment="sandbox",
        )

    def test_po_maps_to_bill_vendor_ref(self):
        po_data = {
            "id": 42,
            "supplier_name": "Acme Farms",
            "external_vendor_id": "56",
            "product_name": "Organic Oats 1kg",
            "external_item_id": "101",
            "quantity": Decimal("100"),
            "cost_per_unit": Decimal("5.00"),
            "total_cost": Decimal("500.00"),
            "order_date": "2024-01-15",
            "notes": "",
            "supplier_payment_terms": "Net30",
        }
        bill = self.adapter.map_po_to_bill(po_data)

        assert bill["VendorRef"]["value"] == "56"
        assert bill["VendorRef"]["name"] == "Acme Farms"

    def test_po_maps_to_bill_total(self):
        po_data = {
            "id": 42,
            "supplier_name": "Acme Farms",
            "external_vendor_id": "56",
            "product_name": "Oats",
            "external_item_id": "101",
            "quantity": Decimal("10"),
            "cost_per_unit": Decimal("5.00"),
            "total_cost": Decimal("50.00"),
            "order_date": "2024-01-15",
            "notes": "",
            "supplier_payment_terms": "Net30",
        }
        bill = self.adapter.map_po_to_bill(po_data)
        assert bill["TotalAmt"] == 50.0

    def test_due_date_net30(self):
        po_data = {
            "id": 1, "supplier_name": "S", "external_vendor_id": "1",
            "product_name": "P", "external_item_id": "2",
            "quantity": Decimal("1"), "cost_per_unit": Decimal("10"),
            "total_cost": Decimal("10"), "order_date": "2024-01-01",
            "notes": "", "supplier_payment_terms": "Net30",
        }
        bill = self.adapter.map_po_to_bill(po_data)
        assert bill["DueDate"] == "2024-01-31"

    def test_supplier_maps_to_vendor(self):
        supplier = {
            "id": 1, "name": "Acme Farms",
            "email": "orders@acme.com", "phone": "555-1234",
            "address": "100 Farm Rd", "payment_terms": "Net30", "notes": "",
        }
        vendor = self.adapter.map_supplier_to_vendor(supplier)
        assert vendor["DisplayName"] == "Acme Farms"
        assert vendor["PrimaryEmailAddr"]["Address"] == "orders@acme.com"
        assert vendor["TermRef"]["name"] == "Net 30"

    def test_sync_bill_raises_without_credentials(self):
        adapter = QuickBooksAdapter(client_id="", realm_id="")
        with pytest.raises(IntegrationNotConfiguredError):
            adapter.sync_purchase_bill({})


# ---------------------------------------------------------------------------
# NetSuite Supplier → Vendor mapping
# ---------------------------------------------------------------------------

class TestNetSuiteMapping:
    def setup_method(self):
        self.adapter = NetSuiteAdapter(account_id="1234567", subsidiary_id="1")

    def test_supplier_maps_to_vendor_company_name(self):
        supplier = {
            "id": 1, "name": "Acme Farms", "email": "orders@acme.com",
            "phone": "555-1234", "address": "100 Farm Rd",
            "payment_terms": "Net30", "notes": "Priority vendor", "active": True,
        }
        vendor = self.adapter.map_supplier_to_vendor(supplier)
        assert vendor["companyName"] == "Acme Farms"
        assert vendor["email"] == "orders@acme.com"

    def test_supplier_maps_subsidiary(self):
        supplier = {
            "id": 1, "name": "Farms Inc", "email": "", "phone": "",
            "address": "", "payment_terms": "", "notes": "", "active": True,
        }
        vendor = self.adapter.map_supplier_to_vendor(supplier)
        assert vendor["subsidiary"]["id"] == "1"

    def test_inactive_supplier(self):
        supplier = {
            "id": 1, "name": "Old Vendor", "email": "", "phone": "",
            "address": "", "payment_terms": "", "notes": "", "active": False,
        }
        vendor = self.adapter.map_supplier_to_vendor(supplier)
        assert vendor["isInactive"] is True

    def test_sync_bill_raises_without_account(self):
        adapter = NetSuiteAdapter(account_id="")
        with pytest.raises(IntegrationNotConfiguredError):
            adapter.sync_purchase_bill({})


# ---------------------------------------------------------------------------
# Registry — graceful degradation
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_shopify_returns_none_when_unconfigured(self, settings):
        settings.SHOPIFY_WEBHOOK_SECRET = ""
        assert get_shopify_adapter() is None

    def test_shopify_returns_adapter_when_configured(self, settings):
        settings.SHOPIFY_WEBHOOK_SECRET = "mysecret"
        adapter = get_shopify_adapter()
        assert adapter is not None
        assert adapter.platform_name == "Shopify"

    def test_quickbooks_returns_none_when_unconfigured(self, settings):
        settings.QUICKBOOKS_CLIENT_ID = ""
        assert get_quickbooks_adapter() is None

    def test_netsuite_returns_none_when_unconfigured(self, settings):
        settings.NETSUITE_ACCOUNT_ID = ""
        assert get_netsuite_adapter() is None

    def test_integration_status_all_false_when_unconfigured(self, settings):
        settings.SHOPIFY_WEBHOOK_SECRET = ""
        settings.AMAZON_SELLER_ID = ""
        settings.QUICKBOOKS_CLIENT_ID = ""
        settings.NETSUITE_ACCOUNT_ID = ""
        status = get_integration_status()
        assert status == {
            "shopify": False,
            "amazon": False,
            "quickbooks": False,
            "netsuite": False,
        }
