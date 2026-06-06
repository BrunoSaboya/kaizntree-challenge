"""
Management command: seed_demo
Creates or seeds organizations with realistic CPG data for evaluation.

Usage:
    # Create the default Green Harvest Co. demo account from scratch
    python manage.py seed_demo

    # Wipe and recreate the default demo account
    python manage.py seed_demo --reset

    # Seed data into an existing account (uses the 'drinks' preset for Drink Co)
    python manage.py seed_demo --email owner@drinkco.com --preset drinks

Available presets: harvest (default), drinks
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

# ── Default demo account ──────────────────────────────────────────────────────
DEMO_EMAIL = "demo@kaizntree.com"
DEMO_PASSWORD = "demo1234"
DEMO_ORG = "Green Harvest Co."

# ── Preset: harvest (food / pantry CPG) ───────────────────────────────────────
HARVEST = {
    "suppliers": [
        {"name": "Pacific Oat Farms", "email": "orders@pacoat.com", "lead_time_days": 7, "payment_terms": "Net 30"},
        {"name": "Alpine Dairy Co.", "email": "supply@alpinedairy.com", "lead_time_days": 5, "payment_terms": "Net 15"},
        {"name": "Sunrise Nuts & Seeds", "email": "hello@sunrisenuts.com", "lead_time_days": 10, "payment_terms": "Net 30"},
    ],
    "products": [
        {"name": "Organic Oat Milk", "sku": "OAT-001", "unit_type": UnitType.L, "description": "Cold-pressed oat milk, barista grade", "min_stock_quantity": 50},
        {"name": "Almond Butter", "sku": "ALM-002", "unit_type": UnitType.KG, "description": "Stone-ground almond butter, no additives", "min_stock_quantity": 20},
        {"name": "Granola Mix", "sku": "GRN-003", "unit_type": UnitType.KG, "description": "House-blend granola with seeds and dried fruit", "min_stock_quantity": 30},
        {"name": "Coconut Water", "sku": "COC-004", "unit_type": UnitType.ML, "description": "Pure coconut water, 330 ml bottles", "min_stock_quantity": 100},
        {"name": "Protein Bar", "sku": "PRO-005", "unit_type": UnitType.COUNT, "description": "Plant-based protein bar, 60 g each", "min_stock_quantity": 200},
    ],
    # (product_idx, supplier_idx, quantity, cost_per_unit, days_ago, lot_id)
    "purchase_orders": [
        (0, 0, Decimal("500"), Decimal("1.20"), 60, "LOT-OAT-A1"),
        (0, 0, Decimal("300"), Decimal("1.15"), 30, "LOT-OAT-A2"),
        (1, 2, Decimal("200"), Decimal("4.50"), 55, "LOT-ALM-B1"),
        (1, 2, Decimal("100"), Decimal("4.80"), 20, "LOT-ALM-B2"),
        (2, 2, Decimal("400"), Decimal("2.10"), 50, "LOT-GRN-C1"),
        (3, 1, Decimal("1000"), Decimal("0.45"), 45, "LOT-COC-D1"),
        (4, 2, Decimal("600"), Decimal("1.80"), 40, "LOT-PRO-E1"),
    ],
    # (product_idx, lot_id, quantity, price_per_unit, days_ago)
    "sales_orders": [
        (0, "LOT-OAT-A1", Decimal("200"), Decimal("3.50"), 50),
        (0, "LOT-OAT-A1", Decimal("150"), Decimal("3.60"), 40),
        (0, "LOT-OAT-A2", Decimal("100"), Decimal("3.55"), 15),
        (1, "LOT-ALM-B1", Decimal("80"), Decimal("12.00"), 48),
        (1, "LOT-ALM-B1", Decimal("60"), Decimal("12.50"), 35),
        (2, "LOT-GRN-C1", Decimal("180"), Decimal("5.80"), 42),
        (3, "LOT-COC-D1", Decimal("400"), Decimal("1.20"), 38),
        (4, "LOT-PRO-E1", Decimal("250"), Decimal("4.50"), 33),
        (4, "LOT-PRO-E1", Decimal("150"), Decimal("4.60"), 20),
    ],
    # (product_idx, supplier_idx, quantity, cost_per_unit)
    "draft_pos": [
        (0, 0, Decimal("400"), Decimal("1.18")),
        (2, 2, Decimal("300"), Decimal("2.05")),
    ],
    # (product_idx, lot_id, quantity, price_per_unit)
    "draft_sos": [
        (1, "LOT-ALM-B2", Decimal("40"), Decimal("13.00")),
        (4, "LOT-PRO-E1", Decimal("80"), Decimal("4.75")),
    ],
}

# ── Preset: drinks (beverage CPG) ─────────────────────────────────────────────
DRINKS = {
    "suppliers": [
        {"name": "Blue Ridge Springs", "email": "supply@blueridgesprings.com", "lead_time_days": 5, "payment_terms": "Net 30"},
        {"name": "Vitality Ingredients", "email": "orders@vitalityingredients.com", "lead_time_days": 8, "payment_terms": "Net 15"},
        {"name": "Ferment & Co.", "email": "hello@fermentco.com", "lead_time_days": 14, "payment_terms": "Net 30"},
    ],
    "products": [
        {"name": "Sparkling Mineral Water", "sku": "SPW-001", "unit_type": UnitType.ML, "description": "Naturally carbonated mineral water, 500 ml bottles", "min_stock_quantity": 200},
        {"name": "Cold Brew Coffee", "sku": "CBR-002", "unit_type": UnitType.L, "description": "Single-origin cold brew, nitrogen-infused", "min_stock_quantity": 40},
        {"name": "Ginger Kombucha", "sku": "KOM-003", "unit_type": UnitType.L, "description": "Live-culture kombucha, ginger & lemon", "min_stock_quantity": 60},
        {"name": "Electrolyte Powder", "sku": "ELP-004", "unit_type": UnitType.G, "description": "Coconut water electrolyte blend, 30 g sachets", "min_stock_quantity": 500},
        {"name": "Energy Shot", "sku": "ENS-005", "unit_type": UnitType.COUNT, "description": "Natural caffeine & B-vitamin shot, 60 ml each", "min_stock_quantity": 300},
    ],
    "purchase_orders": [
        (0, 0, Decimal("2000"), Decimal("0.38"), 55, "LOT-SPW-A1"),
        (0, 0, Decimal("1500"), Decimal("0.36"), 25, "LOT-SPW-A2"),
        (1, 1, Decimal("300"), Decimal("2.10"), 50, "LOT-CBR-B1"),
        (1, 1, Decimal("200"), Decimal("2.25"), 18, "LOT-CBR-B2"),
        (2, 2, Decimal("500"), Decimal("1.60"), 45, "LOT-KOM-C1"),
        (3, 1, Decimal("8000"), Decimal("0.08"), 40, "LOT-ELP-D1"),
        (4, 1, Decimal("800"), Decimal("1.20"), 35, "LOT-ENS-E1"),
    ],
    "sales_orders": [
        (0, "LOT-SPW-A1", Decimal("800"), Decimal("0.95"), 48),
        (0, "LOT-SPW-A1", Decimal("600"), Decimal("0.98"), 35),
        (0, "LOT-SPW-A2", Decimal("500"), Decimal("0.99"), 12),
        (1, "LOT-CBR-B1", Decimal("120"), Decimal("5.50"), 43),
        (1, "LOT-CBR-B1", Decimal("80"), Decimal("5.75"), 30),
        (2, "LOT-KOM-C1", Decimal("200"), Decimal("4.20"), 38),
        (3, "LOT-ELP-D1", Decimal("3000"), Decimal("0.22"), 33),
        (4, "LOT-ENS-E1", Decimal("350"), Decimal("3.50"), 28),
        (4, "LOT-ENS-E1", Decimal("200"), Decimal("3.60"), 14),
    ],
    "draft_pos": [
        (0, 0, Decimal("2000"), Decimal("0.35")),
        (2, 2, Decimal("400"), Decimal("1.55")),
    ],
    "draft_sos": [
        (1, "LOT-CBR-B2", Decimal("60"), Decimal("5.80")),
        (4, "LOT-ENS-E1", Decimal("100"), Decimal("3.65")),
    ],
}

PRESETS = {"harvest": HARVEST, "drinks": DRINKS}


class Command(BaseCommand):
    help = "Seed an organization with realistic CPG data for evaluation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email", type=str, default=None,
            help="Seed into an existing user's org. If omitted, creates the default demo account.",
        )
        parser.add_argument(
            "--preset", type=str, default="harvest", choices=list(PRESETS),
            help="Data preset to use: 'harvest' (food, default) or 'drinks' (beverages).",
        )
        parser.add_argument(
            "--reset", action="store_true",
            help="When used without --email: wipe the default demo account and recreate it.",
        )

    def handle(self, *args, **options):
        preset = PRESETS[options["preset"]]
        email = options["email"]

        if email:
            self._seed_existing(email, preset)
        else:
            if options["reset"]:
                self._wipe_default()
            elif User.objects.filter(email=DEMO_EMAIL).exists():
                self.stdout.write(self.style.WARNING(
                    f"Demo account already exists ({DEMO_EMAIL}). Use --reset to recreate."
                ))
                return
            with transaction.atomic():
                self._create_default(preset)
            self.stdout.write(self.style.SUCCESS(
                f"\nDemo account ready:\n  Email:    {DEMO_EMAIL}\n  Password: {DEMO_PASSWORD}\n  Org:      {DEMO_ORG}\n"
            ))

    def _seed_existing(self, email, preset):
        user = User.objects.filter(email=email).first()
        if not user:
            self.stdout.write(self.style.ERROR(f"No user found with email: {email}"))
            return
        org = user.organization
        if not org:
            self.stdout.write(self.style.ERROR(f"User {email} has no organization."))
            return
        with transaction.atomic():
            self._populate(org, preset)
        self.stdout.write(self.style.SUCCESS(f"\nSeeded org '{org.name}' for {email}.\n"))

    def _wipe_default(self):
        users = User.objects.filter(email=DEMO_EMAIL)
        if users.exists():
            org = users.first().organization
            if org:
                org.delete()
            users.delete()
            self.stdout.write("Existing demo data removed.")

    def _create_default(self, preset):
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
        self._populate(org, preset)

    def _populate(self, org, preset):
        suppliers = [Supplier.objects.create(organization=org, **s) for s in preset["suppliers"]]
        products = [Product.objects.create(organization=org, **p) for p in preset["products"]]
        today = date.today()

        stock_map = {}
        for prod_i, sup_i, qty, cpu, days_ago, lot in preset["purchase_orders"]:
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

        for prod_i, lot, qty, ppu, days_ago in preset["sales_orders"]:
            so = SalesOrder.objects.create(
                organization=org,
                product=products[prod_i],
                stock=stock_map[lot],
                quantity=qty,
                price_per_unit=ppu,
                order_date=today - timedelta(days=days_ago),
            )
            confirm_sales_order(so)

        for prod_i, sup_i, qty, cpu in preset["draft_pos"]:
            PurchaseOrder.objects.create(
                organization=org,
                product=products[prod_i],
                supplier=suppliers[sup_i],
                quantity=qty,
                cost_per_unit=cpu,
                order_date=today,
            )

        for prod_i, lot, qty, ppu in preset["draft_sos"]:
            SalesOrder.objects.create(
                organization=org,
                product=products[prod_i],
                stock=stock_map[lot],
                quantity=qty,
                price_per_unit=ppu,
                order_date=today,
            )
