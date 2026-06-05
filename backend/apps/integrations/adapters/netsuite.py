"""
NetSuite SuiteScript REST adapter — implements ERPAdapter for NetSuite REST API.

Authentication: Token-Based Authentication (TBA) with HMAC-SHA256 OAuth 1.0a
  Unlike most modern APIs, NetSuite REST uses OAuth 1.0a (not OAuth 2.0) for TBA:
  - Consumer Key + Consumer Secret (from NetSuite integration record)
  - Token ID + Token Secret (per user, generated in NetSuite > Setup > Users > Tokens)
  - Each request is signed: Authorization: OAuth realm="...", oauth_consumer_key="...",
    oauth_token="...", oauth_signature_method="HMAC-SHA256", oauth_timestamp="...",
    oauth_nonce="...", oauth_signature="..."

  Reference: https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_4393648056.html

  NetSuite also supports OAuth 2.0 (machine-to-machine) via SuiteCloud Developer Framework,
  but TBA is more widely deployed in mid-market CPG companies.

REST API base URL:
  https://{account_id}.suitetalk.api.netsuite.com/services/rest/record/v1/

Key NetSuite record types for CPG:
  - vendor         → Kaizntree Supplier
  - vendorBill     → Confirmed PurchaseOrder (AP)
  - salesOrder     → Confirmed SalesOrder (AR)
  - inventoryItem  → Product (tracks cost method: FIFO/AVCO — critical for CPG)
  - inventoryAdjustment → Manual stock correction

VendorBill object shape (NetSuite REST API):
  {
    "entity": {"id": "123", "refName": "Acme Farms"},
    "tranDate": "2024-01-15",
    "dueDate": "2024-02-14",
    "memo": "Kaizntree PO #42",
    "item": {
      "items": [
        {
          "item": {"id": "456", "refName": "Organic Oats 1kg"},
          "quantity": 100,
          "rate": 5.00,
          "amount": 500.00,
          "account": {"id": "789", "refName": "Cost of Goods Sold"}
        }
      ]
    }
  }

Subsidiary awareness:
  NetSuite OneWorld (multi-subsidiary) requires a subsidiary field on every record.
  Mid-market CPG brands on OneWorld must include: "subsidiary": {"id": "1"}.
  Single-subsidiary NetSuite accounts omit this field.
"""

from datetime import datetime
from decimal import Decimal

from .base import ERPAdapter, ERPBillPayload, IntegrationNotConfiguredError


class NetSuiteAdapter(ERPAdapter):
    """
    NetSuite SuiteScript REST API adapter (TBA OAuth 1.0a).

    Required settings (via registry):
      NETSUITE_ACCOUNT_ID       — e.g. 1234567 (or 1234567_SB1 for sandbox)
      NETSUITE_CONSUMER_KEY     — from NetSuite integration record
      NETSUITE_CONSUMER_SECRET
      NETSUITE_TOKEN_ID         — per-user token
      NETSUITE_TOKEN_SECRET
      NETSUITE_SUBSIDIARY_ID    — required for OneWorld, omit for single-sub
    """

    def __init__(self, account_id: str, subsidiary_id: str = "1", **kwargs):
        self._account_id = account_id
        self._subsidiary_id = subsidiary_id
        self._base_url = (
            f"https://{account_id}.suitetalk.api.netsuite.com/services/rest/record/v1"
        )

    @property
    def platform_name(self) -> str:
        return "NetSuite"

    def map_supplier_to_vendor(self, supplier_data: dict) -> dict:
        """
        Build a NetSuite vendor record from a Kaizntree Supplier dict.

        Returns a dict for POST {base_url}/vendor.

        Payment terms mapping: NetSuite uses term internal IDs, not strings.
        Common IDs (vary by account): Net 30 = 5, Net 60 = 6, Net 15 = 4.
        In production, query GET {base_url}/term to resolve IDs.
        """
        vendor = {
            "companyName": supplier_data["name"],
            "email": supplier_data.get("email", ""),
            "phone": supplier_data.get("phone", ""),
            "comments": supplier_data.get("notes", ""),
            "isInactive": not supplier_data.get("active", True),
        }

        if self._subsidiary_id:
            vendor["subsidiary"] = {"id": self._subsidiary_id}

        if supplier_data.get("address"):
            vendor["addressBook"] = {
                "items": [
                    {
                        "defaultBilling": True,
                        "addressBookAddress": {"addr1": supplier_data["address"]},
                    }
                ]
            }

        return vendor

    def map_po_to_vendor_bill(self, po_data: dict) -> dict:
        """
        Build a NetSuite vendorBill record from a confirmed Kaizntree PurchaseOrder.

        po_data keys: id, supplier_name, external_vendor_id, product_name,
        external_item_id, external_cogs_account_id, quantity, cost_per_unit,
        total_cost, order_date, notes.

        NetSuite bill lines require an expense account (COGS or Inventory asset).
        Caller must resolve external_cogs_account_id from the chart of accounts.
        """
        total = float(Decimal(str(po_data.get("total_cost", 0))))
        unit_price = float(Decimal(str(po_data.get("cost_per_unit", 0))))
        qty = float(Decimal(str(po_data.get("quantity", 0))))

        bill = {
            "entity": {
                "id": str(po_data.get("external_vendor_id", "")),
                "refName": po_data.get("supplier_name", ""),
            },
            "tranDate": str(po_data.get("order_date", "")),
            "memo": po_data.get("notes", f"Kaizntree PO #{po_data.get('id')}"),
            "item": {
                "items": [
                    {
                        "item": {
                            "id": str(po_data.get("external_item_id", "")),
                            "refName": po_data.get("product_name", ""),
                        },
                        "quantity": qty,
                        "rate": unit_price,
                        "amount": total,
                        "account": {
                            "id": str(po_data.get("external_cogs_account_id", "")),
                        },
                    }
                ]
            },
        }

        if self._subsidiary_id:
            bill["subsidiary"] = {"id": self._subsidiary_id}

        return bill

    def sync_purchase_bill(self, po_data: dict) -> str:
        """
        POST a vendorBill to NetSuite for a confirmed PurchaseOrder.

        Real implementation:
          import requests
          from requests_oauthlib import OAuth1
          oauth = OAuth1(consumer_key, consumer_secret, token_id, token_secret,
                         signature_method="HMAC-SHA256",
                         realm=f"NetSuite:{account_id}")
          resp = requests.post(
              f"{self._base_url}/vendorBill",
              json=self.map_po_to_vendor_bill(po_data),
              auth=oauth,
              headers={"Content-Type": "application/json"},
          )
          # NetSuite returns the internal ID in the Location header:
          # Location: /services/rest/record/v1/vendorBill/{id}
          return resp.headers["Location"].split("/")[-1]
        """
        if not self._account_id:
            raise IntegrationNotConfiguredError(
                "NETSUITE_ACCOUNT_ID is required. Set TBA credentials in .env."
            )
        raise NotImplementedError(
            "sync_purchase_bill requires valid NetSuite TBA credentials."
        )

    def sync_supplier(self, supplier_data: dict) -> str:
        """
        POST/PATCH a vendor record to NetSuite for a Kaizntree Supplier.

        Idempotency: search by companyName using SuiteQL:
          POST {base_url}/../query/v1/suiteql
          {"q": "SELECT id FROM vendor WHERE companyName = ?"}
        """
        if not self._account_id:
            raise IntegrationNotConfiguredError(
                "NETSUITE_ACCOUNT_ID is required."
            )
        raise NotImplementedError("sync_supplier requires NetSuite TBA credentials.")

    def pull_chart_of_accounts(self) -> list[dict]:
        """
        Query accounts via SuiteQL:
          POST {base_url}/../query/v1/suiteql
          {"q": "SELECT id, fullName, acctType, currency FROM account ORDER BY fullName"}

        CPG-relevant account types: OthAsset (Inventory), COGS, Income, AcctPay.
        """
        if not self._account_id:
            raise IntegrationNotConfiguredError("NETSUITE_ACCOUNT_ID is required.")
        raise NotImplementedError("pull_chart_of_accounts requires NetSuite credentials.")

    def pull_bills(self, since: datetime) -> list[ERPBillPayload]:
        """
        Query vendorBills via SuiteQL:
          {"q": "SELECT id, entity, tranDate, dueDate, total FROM vendorBill
                 WHERE tranDate >= ? ORDER BY tranDate DESC"}
        """
        if not self._account_id:
            raise IntegrationNotConfiguredError("NETSUITE_ACCOUNT_ID is required.")
        raise NotImplementedError("pull_bills requires NetSuite credentials.")
