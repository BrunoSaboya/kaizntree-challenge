"""
Abstract adapter interfaces for e-commerce and ERP platform integrations.

Each platform (Shopify, Amazon, QuickBooks, NetSuite) implements one of these
base classes. The registry (integrations/registry.py) returns the correct
concrete adapter based on available credentials, so call sites never import
platform-specific code directly.

Design goals:
- Graceful degradation: adapters raise IntegrationNotConfiguredError when
  credentials are absent, not ImportError or AttributeError.
- Data isolation: all methods accept the owning user so data never leaks across
  tenants regardless of the underlying platform's multi-tenancy model.
- Testability: adapters are pure Python — no Django ORM in the adapter layer.
  The views/services layer handles DB writes after receiving the mapped dict.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


class IntegrationNotConfiguredError(Exception):
    """Raised when required credentials are absent for an adapter."""


# ---------------------------------------------------------------------------
# Shared data transfer objects
# ---------------------------------------------------------------------------


@dataclass
class ExternalLineItem:
    """A single line on an external order (one SKU / product)."""
    external_sku: str
    external_product_name: str
    quantity: Decimal
    unit_price: Decimal
    currency: str = "USD"
    notes: str = ""


@dataclass
class ExternalOrder:
    """Normalised order payload as returned by any e-commerce adapter."""
    platform: str                        # "shopify" | "amazon"
    external_id: str                     # platform-native order ID
    order_date: date
    customer_name: str
    customer_email: str
    line_items: list[ExternalLineItem] = field(default_factory=list)
    shipping_address: str = ""
    notes: str = ""
    raw_payload: dict = field(default_factory=dict)  # full original payload for audit


@dataclass
class ERPBillPayload:
    """Normalised bill/payable payload for ERP sync."""
    external_vendor_id: str
    external_bill_id: str
    amount: Decimal
    currency: str
    due_date: Optional[date]
    line_items: list[dict] = field(default_factory=list)
    reference: str = ""


# ---------------------------------------------------------------------------
# E-commerce adapter interface
# ---------------------------------------------------------------------------


class EcommerceAdapter(ABC):
    """
    Common interface for e-commerce platform adapters.

    Implementations: ShopifyAdapter, AmazonAdapter
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Human-readable platform name, e.g. 'Shopify'."""

    @abstractmethod
    def validate_webhook(self, payload: bytes, signature_header: str) -> bool:
        """
        Verify that a webhook payload was sent by the platform.

        Each platform uses a different scheme:
        - Shopify: HMAC-SHA256 of raw body using the webhook secret
        - Amazon: SNS message signature (RSA + SHA1 over canonical fields)

        Returns True if valid, False otherwise. Never raises.
        """

    @abstractmethod
    def map_order_to_sales_order(self, raw_order: dict) -> dict:
        """
        Map a platform-native order dict to a SalesOrderSerializer-compatible dict.

        Caller is responsible for:
        1. Looking up the internal product_id by matching external_sku
        2. Looking up or creating a Stock entry
        3. POSTing to the SalesOrder create endpoint or calling the service layer

        Returns a dict with keys: product_id (None if unmatched), quantity,
        price_per_unit, order_date, notes, external_id, external_sku.
        """

    @abstractmethod
    def pull_orders(self, since: datetime) -> list[ExternalOrder]:
        """
        Fetch orders created since `since` from the platform API.

        Real implementation requires platform credentials. Stub raises
        IntegrationNotConfiguredError until credentials are configured.
        """

    @abstractmethod
    def push_inventory_update(self, sku: str, qty: int) -> None:
        """
        Push a stock quantity update back to the platform.

        Used to keep platform inventory in sync after a sales order is
        confirmed or cancelled in Kaizntree.
        """


# ---------------------------------------------------------------------------
# ERP adapter interface
# ---------------------------------------------------------------------------


class ERPAdapter(ABC):
    """
    Common interface for ERP / accounting platform adapters.

    Implementations: QuickBooksAdapter, NetSuiteAdapter
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Human-readable platform name, e.g. 'QuickBooks Online'."""

    @abstractmethod
    def sync_purchase_bill(self, po_data: dict) -> str:
        """
        Create or update a Bill in the ERP system for a confirmed PurchaseOrder.

        po_data keys: id, supplier_name, product_name, quantity, cost_per_unit,
        total_cost, order_date, notes, supplier_payment_terms.

        Returns the platform's external bill ID (for audit / reconciliation).
        """

    @abstractmethod
    def sync_supplier(self, supplier_data: dict) -> str:
        """
        Create or update a Vendor/Supplier record in the ERP.

        supplier_data keys: id, name, email, phone, address, payment_terms, notes.

        Returns the platform's external vendor ID.
        """

    @abstractmethod
    def pull_chart_of_accounts(self) -> list[dict]:
        """
        Return the chart of accounts from the ERP.

        Each entry: {id, name, account_type, account_subtype, currency}.
        Used to let users map internal cost categories to ERP accounts.
        """

    @abstractmethod
    def pull_bills(self, since: datetime) -> list[ERPBillPayload]:
        """
        Fetch payable bills created since `since` from the ERP.

        Used for two-way reconciliation: detect bills entered directly in the
        ERP that don't have a matching Kaizntree PurchaseOrder.
        """
