"""
Management command: seed_demo
Creates (or resets) a demo organization with realistic CPG data so evaluators
can log in immediately and see a populated dashboard.

Usage:
    python manage.py seed_demo              # create if not present
    python manage.py seed_demo --reset      # wipe and recreate
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.inventory.models import Product, UnitType
from apps.orders.models import PurchaseOrder, SalesOrder
from apps.orders.services import confirm_purchase_order, confirm_sales_order
from apps.suppliers.models import Supplier
from apps.users.models import Organization

User = get_user_model()

DEMO_EMAIL = "demo@kaizntree.com"
DEMO_PASSWORD = "demo1234"
DEMO_ORG = "Green Harvest Co."

SUPPLIERS = [
    {"name": "Pacific Oat Farms", "email": "orders@pacoat.com", "lead_time_days": 7, "payment_terms": "Net 30"},
    {"name": "Alpine Dairy Co.", "email": "supply@alpinedairy.com", "lead_time_days": 5, "payment_terms": "Net 15"},
    {"name": "Sunrise Nuts & Seeds", "email": "hello@sunrisenuts.com", "lead_time_days": 10, "payment_terms": "Net 30"},
]

PRODUCTS = [
    {"name": "Organic Oat Milk", "sku": "OAT-001", "unit_type": UnitType.L, "description": "Cold-pressed oat milk, barista grade", "min_stock_quantity": 50},
    {"name": "Almond Butter", "sku": "ALM-002", "unit_type": UnitType.KG, "description": "Stone-ground almond butter, no additives", "min_stock_quantity": 20},
    {"name": "Granola Mix", "sku": "GRN-003", "unit_type": UnitType.KG, "description": "House-blend granola with seeds and dried fruit", "min_stock_quantity": 30},
    {"name": "Coconut Water", "sku": "COC-004", "unit_type": UnitType.ML, "description": "Pure coconut water, 330 ml bottles", "min_stock_quantity": 100},
    {"name": "Protein Bar", "sku": "PRO-005", "unit_type": UnitType.COUNT, "description": "Plant-based protein bar, 60 g each", "min_stock_quantity": 200},
]

# (product_idx, supplier_idx, quantity, cost_per_unit, days_ago, lot)
PURCHASE_ORDERS = [
    (0, 0, Decimal("500"), Decimal("1.20"), 60, "LOT-OAT-A1"),
    (0, 0, Decimal("300"), Decimal("1.15"), 30, "LOT-OAT-A2"),
    (1, 2, Decimal("200"), Decimal("4.50"), 55, "LOT-ALM-B1"),
    (1, 2, Decimal("100"), Decimal("4.80"), 20, "LOT-ALM-B2"),
    (2, 2, Decimal("400"), Decimal("2.10"), 50, "LOT-GRN-C1"),
    (3, 1, Decimal("1000"), Decimal("0.45"), 45, "LOT-COC-D1"),
    (4, 2, Decimal("600"), Decimal("1.80"), 40, "LOT-PRO-E1"),
]

# (product_idx, lot, quantity, price_per_unit, days_ago)
SALES_ORDERS = [
    (0, "LOT-OAT-A1", Decimal("200"), Decimal("3.50"), 50),
    (0, "LOT-OAT-A1", Decimal("150"), Decimal("3.60"), 40),
    (0, "LOT-OAT-A2", Decimal("100"), Decimal("3.55"), 15),
    (1, "LOT-ALM-B1", Decimal("80"), Decimal("12.00"), 48),
    (1, "LOT-ALM-B1", Decimal("60"), Decimal("12.50"), 35),
    (2, "LOT-GRN-C1", Decimal("180"), Decimal("5.80"), 42),
    (3, "LOT-COC-D1", Decimal("400"), Decimal("1.20"), 38),
    (4, "LOT-PRO-E1", Decimal("250"), Decimal("4.50"), 33),
    (4, "LOT-PRO-E1", Decimal("150"), Decimal("4.60"), 20),
]

# Draft orders so the pipeline view isn't empty
DRAFT_POS = [
    (0, 0, Decimal("400"), Decimal("1.18")),
    (2, 2, Decimal("300"), Decimal("2.05")),
]

DRAFT_SOS = [
    (1, "LOT-ALM-B2", Decimal("40"), Decimal("13.00")),
    (4, "LOT-PRO-E1", Decimal("80"), Decimal("4.75")),
]


class Command(BaseCommand):
    help = "Seed a demo organization with realistic CPG data for evaluation."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing demo data and recreate it.")

    def handle(self, *args, **options):
        if options["reset"]:
            self._wipe()
        elif User.objects.filter(email=DEMO_EMAIL).exists():
            self.stdout.write(self.style.WARNING(f"Demo account already exists ({DEMO_EMAIL}). Use --reset to recreate."))
            return

        with transaction.atomic():
            self._seed()

        self.stdout.write(self.style.SUCCESS(
            f"\nDemo account ready:\n  Email:    {DEMO_EMAIL}\n  Password: {DEMO_PASSWORD}\n  Org:      {DEMO_ORG}\n"
        ))

    def _wipe(self):
        users = User.objects.filter(email=DEMO_EMAIL)
        if users.exists():
            org = users.first().organization
            if org:
                org.delete()
            users.delete()
            self.stdout.write("Existing demo data removed.")

    def _seed(self):
        org = Organization.objects.create(name=DEMO_ORG)
        user = User.objects.create_user(
            email=DEMO_EMAIL,
            username="demo",
            password=DEMO_PASSWORD,
            role=User.ROLE_OWNER,
            organization=org,
            first_name="Demo",
            last_name="User",
        )
        org.owner = user
        org.save(update_fields=["owner"])

        suppliers = [Supplier.objects.create(organization=org, **s) for s in SUPPLIERS]
        products = [Product.objects.create(organization=org, **p) for p in PRODUCTS]

        today = date.today()

        # Confirmed purchase orders
        stock_map = {}
        for prod_i, sup_i, qty, cpu, days_ago, lot in PURCHASE_ORDERS:
            po = PurchaseOrder.objects.create(
                organization=org,
                product=products[prod_i],
                supplier=suppliers[sup_i],
                quantity=qty,
                cost_per_unit=cpu,
                order_date=today - timedelta(days=days_ago),
            )
            po = confirm_purchase_order(po, stock_identifier=lot)
            stock_map[lot] = po.stock

        # Confirmed sales orders
        for prod_i, lot, qty, ppu, days_ago in SALES_ORDERS:
            so = SalesOrder.objects.create(
                organization=org,
                product=products[prod_i],
                stock=stock_map[lot],
                quantity=qty,
                price_per_unit=ppu,
                order_date=today - timedelta(days=days_ago),
            )
            confirm_sales_order(so)

        # Draft purchase orders (so pipeline isn't empty)
        for prod_i, sup_i, qty, cpu in DRAFT_POS:
            PurchaseOrder.objects.create(
                organization=org,
                product=products[prod_i],
                supplier=suppliers[sup_i],
                quantity=qty,
                cost_per_unit=cpu,
                order_date=today,
            )

        # Draft sales orders
        for prod_i, lot, qty, ppu in DRAFT_SOS:
            SalesOrder.objects.create(
                organization=org,
                product=products[prod_i],
                stock=stock_map[lot],
                quantity=qty,
                price_per_unit=ppu,
                order_date=today,
            )
