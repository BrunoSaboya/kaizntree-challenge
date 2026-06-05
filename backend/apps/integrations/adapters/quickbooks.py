"""
QuickBooks Online adapter — implements ERPAdapter for the QBO REST API v3.

Authentication: OAuth 2.0 (Authorization Code Flow)
  1. Redirect user to https://appcenter.intuit.com/connect/oauth2 with:
     scope=com.intuit.quickbooks.accounting
  2. Exchange code for access_token + refresh_token (60-day TTL, auto-refresh)
  3. Store realm_id (company ID) returned in the OAuth callback

  Reference: https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization

Key QBO concepts for CPG:
  - Vendor   → Kaizntree Supplier (maps payment_terms to QBO TermRef)
  - Bill     → Confirmed PurchaseOrder (AP payable, debit Inventory asset)
  - Invoice  → Confirmed SalesOrder (AR receivable, credit Inventory)
  - Item     → Product (type=Inventory, requires IncomeAccount + ExpenseAccount + AssetAccount)

Bill object shape (QBO REST API v3):
  {
    "VendorRef": {"value": "56", "name": "Acme Farms"},
    "TxnDate": "2024-01-15",
    "DueDate": "2024-02-14",
    "TotalAmt": 500.00,
    "Line": [
      {
        "DetailType": "ItemBasedExpenseLineDetail",
        "Amount": 500.00,
        "ItemBasedExpenseLineDetail": {
          "ItemRef": {"value": "1", "name": "Organic Oats 1kg"},
          "Qty": 100,
          "UnitPrice": 5.00,
          "BillableStatus": "NotBillable"
        }
      }
    ],
    "APAccountRef": {"value": "33", "name": "Accounts Payable"}
  }

Payment terms mapping (Kaizntree → QBO TermRef name):
  "Net30"  → "Net 30"
  "Net60"  → "Net 60"
  "Net15"  → "Net 15"
  "COD"    → "Due on receipt"
"""

from datetime import datetime
from decimal import Decimal

from .base import ERPAdapter, ERPBillPayload, IntegrationNotConfiguredError


_PAYMENT_TERMS_MAP = {
    "Net30": "Net 30",
    "Net60": "Net 60",
    "Net15": "Net 15",
    "Net45": "Net 45",
    "Net90": "Net 90",
    "COD": "Due on receipt",
    "Prepaid": "Due on receipt",
}


class QuickBooksAdapter(ERPAdapter):
    """
    QuickBooks Online (QBO) REST API v3 adapter.

    Required settings (via registry):
      QUICKBOOKS_CLIENT_ID      — QBO OAuth app client ID
      QUICKBOOKS_CLIENT_SECRET  — QBO OAuth app client secret
      QUICKBOOKS_REALM_ID       — Company ID, returned in OAuth callback
      QUICKBOOKS_ACCESS_TOKEN   — Short-lived (1hr) access token
      QUICKBOOKS_REFRESH_TOKEN  — Long-lived (60d) refresh token
      QUICKBOOKS_ENVIRONMENT    — "sandbox" | "production"
    """

    def __init__(self, client_id: str, realm_id: str = "", environment: str = "sandbox", **kwargs):
        self._client_id = client_id
        self._realm_id = realm_id
        self._environment = environment
        self._base_url = (
            "https://quickbooks.api.intuit.com"
            if environment == "production"
            else "https://sandbox-quickbooks.api.intuit.com"
        )

    @property
    def platform_name(self) -> str:
        return "QuickBooks Online"

    def map_supplier_to_vendor(self, supplier_data: dict) -> dict:
        """
        Build a QBO Vendor object from a Kaizntree Supplier dict.

        supplier_data keys: id, name, email, phone, address, payment_terms, notes.

        Returns a dict ready for POST /v3/company/{realmId}/vendor or
        POST /v3/company/{realmId}/batch (for bulk sync).
        """
        terms_name = _PAYMENT_TERMS_MAP.get(supplier_data.get("payment_terms", ""), "Net 30")

        vendor = {
            "DisplayName": supplier_data["name"],
            "PrimaryEmailAddr": {"Address": supplier_data.get("email", "")},
            "PrimaryPhone": {"FreeFormNumber": supplier_data.get("phone", "")},
            "Notes": supplier_data.get("notes", ""),
            # TermRef requires looking up the TermRef.value from QBO's term list first.
            # Use GET /v3/company/{realmId}/query?query=SELECT * FROM Term
            "TermRef": {"name": terms_name},
        }

        if supplier_data.get("address"):
            vendor["BillAddr"] = {"Line1": supplier_data["address"]}

        return vendor

    def map_po_to_bill(self, po_data: dict) -> dict:
        """
        Build a QBO Bill object from a confirmed Kaizntree PurchaseOrder.

        po_data keys: id, supplier_name, external_vendor_id, product_name,
        external_item_id, quantity, cost_per_unit, total_cost, order_date,
        notes, supplier_payment_terms.

        Caller must supply external_vendor_id (QBO Vendor.Id) and
        external_item_id (QBO Item.Id) — obtained from a prior sync_supplier call
        and item lookup respectively.

        Returns a dict ready for POST /v3/company/{realmId}/bill.
        """
        total = Decimal(str(po_data.get("total_cost", 0)))
        unit_price = Decimal(str(po_data.get("cost_per_unit", 0)))
        qty = Decimal(str(po_data.get("quantity", 0)))

        bill = {
            "VendorRef": {
                "value": str(po_data.get("external_vendor_id", "")),
                "name": po_data.get("supplier_name", ""),
            },
            "TxnDate": str(po_data.get("order_date", "")),
            "TotalAmt": float(total),
            "PrivateNote": po_data.get("notes", f"Kaizntree PO #{po_data.get('id')}"),
            "Line": [
                {
                    "DetailType": "ItemBasedExpenseLineDetail",
                    "Amount": float(total),
                    "ItemBasedExpenseLineDetail": {
                        "ItemRef": {
                            "value": str(po_data.get("external_item_id", "")),
                            "name": po_data.get("product_name", ""),
                        },
                        "Qty": float(qty),
                        "UnitPrice": float(unit_price),
                        "BillableStatus": "NotBillable",
                    },
                }
            ],
        }

        # Calculate DueDate from payment terms
        terms = po_data.get("supplier_payment_terms", "Net30")
        net_days = 30
        for key in ("Net15", "Net30", "Net45", "Net60", "Net90"):
            if key in terms:
                net_days = int(key.replace("Net", ""))
                break
        from datetime import date, timedelta
        if isinstance(po_data.get("order_date"), str):
            order_date = date.fromisoformat(po_data["order_date"])
        else:
            order_date = po_data.get("order_date", date.today())
        bill["DueDate"] = str(order_date + timedelta(days=net_days))

        return bill

    def sync_purchase_bill(self, po_data: dict) -> str:
        """
        POST a Bill to QBO for a confirmed PurchaseOrder.

        Real implementation:
          import requests
          resp = requests.post(
              f"{self._base_url}/v3/company/{self._realm_id}/bill",
              json=self.map_po_to_bill(po_data),
              headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
          )
          return resp.json()["Bill"]["Id"]

        Token refresh: QBO access tokens expire after 1 hour. Use the refresh token
        with POST https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer to get
        a new access token before each API call.
        """
        if not self._client_id or not self._realm_id:
            raise IntegrationNotConfiguredError(
                "QUICKBOOKS_CLIENT_ID and QUICKBOOKS_REALM_ID are required. "
                "Complete the OAuth flow at /integrations/quickbooks/connect/."
            )
        raise NotImplementedError(
            "sync_purchase_bill requires a valid QBO OAuth access token."
        )

    def sync_supplier(self, supplier_data: dict) -> str:
        """
        POST/PATCH a Vendor to QBO for a Kaizntree Supplier.

        Idempotency: search for existing vendor by name before creating:
          GET /v3/company/{realmId}/query?query=SELECT * FROM Vendor WHERE DisplayName = '{name}'
        If found, PATCH with sparse update. If not found, POST.
        """
        if not self._client_id or not self._realm_id:
            raise IntegrationNotConfiguredError(
                "QUICKBOOKS_CLIENT_ID and QUICKBOOKS_REALM_ID are required."
            )
        raise NotImplementedError(
            "sync_supplier requires a valid QBO OAuth access token."
        )

    def pull_chart_of_accounts(self) -> list[dict]:
        """
        GET /v3/company/{realmId}/query?query=SELECT * FROM Account MAXRESULTS 1000

        Returns list of {id, name, account_type, account_subtype, currency}.
        Relevant types for CPG: Inventory (asset), Cost of Goods Sold (expense),
        Sales of Product Income (income), Accounts Payable (liability).
        """
        if not self._client_id or not self._realm_id:
            raise IntegrationNotConfiguredError(
                "QUICKBOOKS credentials are not configured."
            )
        raise NotImplementedError("pull_chart_of_accounts requires QBO credentials.")

    def pull_bills(self, since: datetime) -> list[ERPBillPayload]:
        """
        GET /v3/company/{realmId}/query?query=SELECT * FROM Bill WHERE TxnDate >= '{since.date()}'

        Returned bills are compared against Kaizntree PurchaseOrders to detect
        bills entered directly in QBO (outside Kaizntree) for reconciliation.
        """
        if not self._client_id or not self._realm_id:
            raise IntegrationNotConfiguredError(
                "QUICKBOOKS credentials are not configured."
            )
        raise NotImplementedError("pull_bills requires QBO credentials.")
