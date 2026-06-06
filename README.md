# Kaizntree Inventory Management System

A full-stack, multi-tenant inventory management platform for F&B CPG brands, built as a take-home challenge for Kaizntree. Features demand forecasting, AI-powered invoice parsing, and third-party e-commerce/ERP integrations.

## Live Demo

| | URL |
|---|---|
| **Frontend** | https://kaizntree-challenge.vercel.app |
| **API** | https://kaizntree-challenge-production.up.railway.app/api/v1/ |
| **Swagger UI** | https://kaizntree-challenge-production.up.railway.app/api/schema/swagger-ui/ |

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost |
| Backend API | http://localhost:8000/api/v1/ |
| Swagger UI | http://localhost:8000/api/schema/swagger-ui/ |

**Dev mode** (hot reload for both frontend and backend):

```bash
docker compose up --build   # override file is auto-loaded
# Frontend: http://localhost:5173
```

## Run Tests

```bash
docker compose run --rm backend pytest
```

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.12, Django 5.1, Django REST Framework 3.15 |
| Auth | djangorestframework-simplejwt — httpOnly refresh cookie + in-memory access token |
| API Docs | drf-spectacular (OpenAPI / Swagger UI) |
| Frontend | React 18, TypeScript 5, Vite 5, Mantine 7, TanStack Query v5, Zustand, Zod |
| Infra | Docker Compose, PostgreSQL 16, Nginx, Railway (backend + DB), Vercel (frontend) |
| Tests | pytest-django, factory-boy, pytest-cov |
| CI | GitHub Actions (pytest + tsc) |

## Features

### Multi-Tenant Organizations & Roles

The system is built around isolated organizations. Every user belongs to exactly one organization (except system admins), and all business data — products, stock, orders, suppliers — is scoped to that organization.

Three roles govern access throughout the app:

| Role | Access |
|------|--------|
| **admin** | System-wide: create/manage organizations and users across all orgs. No access to business data. |
| **owner** | Full access to their organization's data + can manage team members. |
| **member** | Full access to their organization's data. Cannot manage users. |

Role enforcement happens at three layers: JWT authentication, DRF permission classes (`IsAdmin`, `IsOwner`, `IsOrgUser`), and automatic queryset filtering by `OrgScopedMixin`.

### Inventory & Products

- Full CRUD for products with SKU, unit type, description, and per-organization uniqueness enforcement
- **Minimum stock threshold** — set a floor quantity per product; the product list highlights products below it
- **Bulk CSV import** — upload a CSV to create many products at once, with per-row Zod validation, live status badges, and a downloadable sample template

### Stock Management & Audit Trail

- Track stock entries per product with lot identifier, quantity, and notes
- **Expiry date tracking** — optional expiry date per stock entry; the dashboard surfaces entries expiring within 30 days
- **Stock movement log** — every inbound/outbound stock event is recorded as an immutable `StockMovement` entry with movement type, signed quantity change, and a reference to the source order. Movement types: `PURCHASE_CONFIRMED`, `SALES_CONFIRMED`, `SALES_CANCELLED`, `MANUAL_ADJUSTMENT`. Viewable in a history drawer on the Stock page.

### Dashboard

- **Financial summary** — total cost, revenue, gross profit, and margin derived from confirmed orders in a single ORM annotation query
- **Order pipeline** — counts of draft/confirmed/cancelled purchase and sales orders
- **Low-stock alerts** — table of products below their minimum threshold
- **Expiring stock** — table of stock entries expiring within 30 days, sorted by closest expiry
- **Revenue vs. cost bar chart** — per-product comparison powered by Mantine Charts
- **Ring progress** — visual profit margin indicator

### Orders

- **Purchase Orders:** create → confirm (creates/increments stock, records movement) → cancel
- **Sales Orders:** create → confirm (validates sufficiency, decrements stock, records movement) → cancel (restores stock if already confirmed, records reversal movement)
- All mutations run in `transaction.atomic()` with `select_for_update()` to prevent race conditions under concurrent requests

### Supplier Management

- Full CRUD for suppliers with name, email, phone, address, payment terms, and lead time (days)
- Soft-delete via `active` flag — deactivated suppliers are hidden from active lists but retained for historical PO references
- Suppliers link to purchase orders and provide lead time for forecasting calculations

### Financials

- Per-product and aggregate profit/margin reporting, always computed live from confirmed orders — no denormalized storage
- Metrics: total cost, total revenue, gross profit, margin %, units purchased/sold, current stock, inventory value

### Demand Forecasting

- **Reorder point recommendations** per product, computed from 30 days of confirmed sales history
- **Safety stock** calculated at a 95% service level: `1.65 × σ_daily × √(lead_time_days)`
- **Reorder point:** `avg_daily_consumption × lead_time_days + safety_stock`
- Status badges: `OK` / `LOW` / `CRITICAL` / `OUT_OF_STOCK`
- Lead time sourced from the product's linked supplier or latest purchase order
- One-click draft PO creation from the forecasting page with recommended quantity pre-filled

### AI-Powered Invoice Parsing

- Paste any free-form invoice, vendor email, or quote into the AI Assist page
- Claude Haiku 4.5 extracts structured data (supplier name, order date, line items) via tool-use
- Fuzzy product matching compares extracted names against your catalog using `difflib.SequenceMatcher` — matches at ≥ 0.5 confidence are highlighted
- Returns a confidence score and extraction notes; user reviews before creating draft POs
- Rate-limited to 10 requests/minute per user
- Degrades gracefully: returns empty extraction if `ANTHROPIC_API_KEY` is absent

### Third-Party Integrations

All integrations use a registry pattern — if credentials are absent, the adapter returns `None` and the API returns `503` with a descriptive message rather than crashing.

| Platform | Type | Auth | Behaviour |
|----------|------|------|-----------|
| **Shopify** | E-commerce | HMAC-SHA256 webhook | `orders/create` webhook creates draft Sales Orders; unmatched SKUs are skipped |
| **Amazon SP-API** | E-commerce | AWS SigV4 + LWA OAuth2 | Polls `GetOrders`; maps `SellerSKU` → `Product.sku` |
| **QuickBooks Online** | ERP/AP | OAuth 2.0 (60-day refresh, auto-renew) | Syncs confirmed POs as Bills; maps Suppliers to Vendors |
| **NetSuite** | ERP/ERP | OAuth 1.0a TBA (HMAC-SHA256) | Syncs vendorBill records and inventoryItem; subsidiary-aware |

A read-only `GET /integrations/status/` endpoint returns which platforms are configured without requiring authentication.

---

## Role & Permission Model

```
System
├── admin (no org)
│   ├── POST /organizations/provision/     — create org + owner atomically
│   ├── GET/PATCH /organizations/          — manage all orgs
│   └── GET/PATCH/DELETE /users/           — manage all users
│
└── Organization
    ├── owner
    │   ├── GET/POST/PATCH/DELETE /org/members/  — manage team members
    │   └── all business endpoints below
    │
    └── member
        ├── /products/, /stock/, /purchase-orders/, /sales-orders/
        ├── /suppliers/, /financials/, /forecasting/
        └── /ai/parse-purchase-order/, /integrations/status/
```

Frontend route guards mirror these boundaries: `AdminRoute`, `OwnerRoute`, and `BusinessRoute` components redirect unauthorized users before any data is fetched.

---

## Project Structure

```
kaizntree-challenge/
├── backend/
│   ├── apps/
│   │   ├── users/          # Custom User + Organization models, JWT auth, RBAC permissions
│   │   ├── inventory/      # Product + Stock + StockMovement models, CRUD API
│   │   ├── orders/         # PurchaseOrder + SalesOrder with confirm/cancel service layer
│   │   ├── financials/     # Profit/margin computation via single annotated ORM query
│   │   ├── suppliers/      # Supplier CRUD, soft-delete
│   │   ├── forecasting/    # Demand signal, safety stock, reorder point computation
│   │   ├── ai_workflows/   # Claude AI invoice parsing with fuzzy product matching
│   │   └── integrations/   # Shopify, Amazon, QuickBooks, NetSuite adapters + registry
│   └── kaizntree/
│       ├── settings/       # base.py / development.py / production.py
│       └── urls.py         # /api/v1/ routing + schema
│
└── frontend/src/
    ├── api/                # Axios client + per-resource API functions
    ├── store/              # Zustand auth store (in-memory access token)
    ├── pages/
    │   ├── DashboardPage.tsx
    │   ├── ProductListPage.tsx / ProductDetailPage.tsx
    │   ├── StockPage.tsx
    │   ├── PurchaseOrderListPage.tsx / SalesOrderListPage.tsx
    │   ├── SuppliersPage.tsx
    │   ├── ForecastingPage.tsx
    │   ├── AIAssistPage.tsx
    │   ├── IntegrationsPage.tsx
    │   ├── OrgMembersPage.tsx          # owner only
    │   ├── admin/AdminUsersPage.tsx    # admin only
    │   └── admin/AdminOrgsPage.tsx     # admin only
    ├── components/
    │   ├── layout/AppShellLayout.tsx   # role-aware navbar, user menu
    │   └── products/ImportProductsModal.tsx
    ├── utils/
    │   ├── csvParser.ts    # RFC-4180-compliant CSV parser (zero dependencies)
    │   ├── formatters.ts   # currency, percent, date, quantity formatters
    │   └── useRole.ts      # isAdmin / isOwner / isMember hook
    └── types/              # TypeScript interfaces mirroring all API shapes
```

---

## Architecture Decisions

### Authentication: Hybrid httpOnly Cookie + In-Memory Access Token

- **Access token** (15 min TTL) — stored in Zustand (memory only). Never touches `localStorage` or the DOM. Sent as `Authorization: Bearer` on every request.
- **Refresh token** (7 days) — stored in two places for resilience:
  - An `httpOnly; SameSite=Lax; Secure` cookie (primary — invisible to JavaScript).
  - `sessionStorage["kz_refresh_token"]` (fallback — used when cookies are blocked by Brave Shields / Safari ITP).

The Axios client has a response interceptor: on any 401 it transparently calls `/auth/refresh/`, updates the in-memory token, and retries the original request. On hard page refresh, `App.tsx` tries the cookie path first, then the `sessionStorage` body path. Either path silently restores the session without re-login.

> **Note:** The `/auth/refresh/` view reads the token from the cookie and injects it into `request._full_data` (the backing store for DRF's read-only `Request.data`) before delegating to `TokenRefreshView`.

### Multi-Tenant Data Isolation via `OrgScopedMixin`

All ViewSets extend `OrgScopedMixin`, which filters every queryset to `organization=request.user.organization`. Because `get_object()` calls `get_queryset()` first, cross-organization access always returns **404**, not 403 — this avoids leaking the existence of other organizations' resources.

### Transactional Stock Mutations

Confirming or cancelling orders modifies stock quantities. Both operations run in `transaction.atomic()` with `select_for_update()` to prevent race conditions under concurrent requests. Stock quantities are updated using a DB-level `F("quantity") + delta` expression — no read-modify-write pattern.

### Financial Computation: Single ORM Query, No Denormalization

All profit/margin metrics are computed at query time via a single annotated queryset using Django's `Sum`, `F`, and `ExpressionWrapper`. No financial data is stored — it's always derived from confirmed orders. The dashboard is always accurate, never stale.

### SKU Uniqueness Per Organization

SKU uniqueness is enforced at two levels: a `validate_sku` check in the serializer (clean 400 response) and a `unique_together = [("organization", "sku")]` DB constraint as a safety net. Two different organizations can use the same SKU; a single organization cannot have two products with the same SKU.

### Demand Forecasting Algorithm

The forecasting service analyses the last 30 days of `SALES_CONFIRMED` stock movements to compute:

```
avg_daily_consumption  = Σ(daily_outbound) / 30
σ_daily                = standard deviation of daily outbound quantities
safety_stock           = 1.65 × σ_daily × √(lead_time_days)     # 95% service level
reorder_point          = avg_daily × lead_time_days + safety_stock
days_of_stock          = current_stock / avg_daily_consumption
recommended_qty        = max(avg_daily × lead_time_days × 2, min_stock_quantity)
```

Lead time is sourced from `supplier.lead_time_days` (if linked) or the most recent purchase order's supplier.

### AI Extraction: Claude Tool Use + Fuzzy Matching

The AI workflow calls Claude Haiku 4.5 with a `tool_use` block that forces structured JSON output — supplier name, order date, and line items. Extracted product names are then fuzzy-matched against the user's catalog using `difflib.SequenceMatcher` with a 0.5 minimum confidence threshold. The endpoint never auto-creates any records; it returns a draft for human review.

### Integration Registry Pattern

Each third-party adapter (Shopify, Amazon, QBO, NetSuite) is registered via a `get_<platform>_adapter()` factory function in `integrations/registry.py`. If the required credentials are absent from the environment, the factory returns `None`. Views check `if adapter is None` and return `503 Service Unavailable` with a human-readable message rather than raising an `ImportError` or `AttributeError`. This allows the app to boot and function without any integration credentials configured.

### CSV Import: Zero-Dependency Parser

`frontend/src/utils/csvParser.ts` implements an RFC-4180-compliant parser that handles quoted fields, escaped quotes, Windows/Unix line endings, and unknown column ordering. Each row is validated client-side with Zod before being submitted, and rows are imported sequentially so partial failures are recoverable without re-uploading the whole file.

---

## API Reference

Interactive docs available at `/api/schema/swagger-ui/` when the backend is running.

### Endpoints Summary

**Auth** — `/api/v1/auth/`
- `POST /login/` — authenticate, returns access token + sets refresh cookie
- `POST /refresh/` — exchange refresh token for new access token
- `POST /logout/` — blacklist refresh token
- `GET /me/` — current user info
- `PUT/PATCH /me/` — update own name or password

**Admin: Users** — `/api/v1/users/` *(IsAdmin)*
- Full CRUD — list all users, create with role + org, update, soft-delete
- `POST /{id}/reactivate/` — re-enable a deactivated user

**Admin: Organizations** — `/api/v1/organizations/` *(IsAdmin)*
- Full CRUD — list, create, update
- `POST /provision/` — atomically create an org + an owner user

**Owner: Members** — `/api/v1/org/members/` *(IsOwner)*
- `GET /` — list members in the owner's org
- `POST /` — invite a new member
- `PATCH /{id}/` — update member name or password
- `DELETE /{id}/` — deactivate member

**Products** — `/api/v1/products/`
- Full CRUD + `?search=` + `?unit_type=` filter
- `GET /{id}/stock/` — stock entries for this product
- `GET /{id}/financials/` — per-product profit/margin
- `GET /{id}/movements/` — stock movement history for this product

**Stock** — `/api/v1/stock/`
- Full CRUD + `?product=` filter
- `GET /expiring_soon/` — entries expiring within `?days=30`
- `GET /{id}/movements/` — movement history for a stock entry

**Purchase Orders** — `/api/v1/purchase-orders/`
- Full CRUD (only drafts can be edited/deleted)
- `POST /{id}/confirm/` — body: `{ stock_identifier, expiry_date?, stock_notes? }` — creates/increments stock, records movement
- `POST /{id}/cancel/`

**Sales Orders** — `/api/v1/sales-orders/`
- Full CRUD (only drafts can be edited/deleted)
- `POST /{id}/confirm/` — decrements stock, records movement (validates sufficiency)
- `POST /{id}/cancel/` — restores stock if was confirmed, records reversal movement

**Suppliers** — `/api/v1/suppliers/`
- Full CRUD + `?search=` + `?active=` filter

**Financials** — `/api/v1/financials/`
- `GET /summary/` — org-wide total cost, revenue, profit, margin, inventory value
- `GET /products/` — per-product breakdown

**Forecasting** — `/api/v1/forecasting/`
- `GET /reorder-recommendations/` — per-product reorder status and recommended order quantity

**AI Workflows** — `/api/v1/ai/`
- `POST /parse-purchase-order/` — body: `{ text }` — Claude extracts supplier, date, line items; returns fuzzy-matched products and confidence score

**Integrations** — `/api/v1/integrations/`
- `GET /status/` — which platforms are configured (public endpoint)
- `POST /shopify/webhook/` — Shopify `orders/create` webhook (HMAC-SHA256 auth)

---

## Cloud Deployment

The app is deployed as two independent services: Railway hosts the Django backend + PostgreSQL database; Vercel hosts the React SPA.

### Backend — Railway

`railway.toml` tells Railway to build from the backend `Dockerfile` (production stage), healthcheck at `GET /health`, and restart on failure.

The production Dockerfile runs `collectstatic` at build time and starts Gunicorn bound to `$PORT`. `entrypoint.sh` waits for PostgreSQL using `pg_isready` before running migrations.

**Required Railway environment variables:**

| Variable | Value |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `kaizntree.settings.production` |
| `DJANGO_SECRET_KEY` | long random string |
| `CORS_ALLOWED_ORIGINS` | `https://kaizntree-challenge.vercel.app` |
| `DATABASE_URL` | *(auto-injected by Railway — add the PostgreSQL plugin)* |

**Optional — AI & Integrations:**

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Enables AI invoice parsing (Claude Haiku) |
| `SHOPIFY_WEBHOOK_SECRET` | Enables Shopify webhook handler |
| `AMAZON_LWA_CLIENT_ID`, `AMAZON_LWA_CLIENT_SECRET`, `AMAZON_REFRESH_TOKEN`, `AMAZON_AWS_*` | Enables Amazon SP-API |
| `QBO_CLIENT_ID`, `QBO_CLIENT_SECRET`, `QBO_REFRESH_TOKEN`, `QBO_REALM_ID` | Enables QuickBooks Online |
| `NETSUITE_ACCOUNT_ID`, `NETSUITE_CONSUMER_KEY`, `NETSUITE_CONSUMER_SECRET`, `NETSUITE_TOKEN_ID`, `NETSUITE_TOKEN_SECRET` | Enables NetSuite |

> `DJANGO_ALLOWED_HOSTS` does **not** need to be set — `production.py` already allows all `*.railway.app` / `*.up.railway.app` patterns plus any custom domain in `RAILWAY_PUBLIC_DOMAIN`.

### Frontend — Vercel

Point Vercel at the `frontend/` subdirectory with build command `npm run build` and output directory `dist`. `frontend/vercel.json` rewrites every route to `index.html` for client-side SPA routing.

**Required Vercel environment variable:**

| Variable | Value |
|---|---|
| `VITE_API_URL` | `https://kaizntree-challenge-production.up.railway.app` |

### Cross-Domain Session Architecture

Because Vercel and Railway are on different domains, session persistence is dual-layered:

1. **httpOnly cookie** (`SameSite=None; Secure`) — set by Railway on every login/refresh. Works in Chrome/Firefox by default.
2. **`sessionStorage["kz_refresh_token"]`** — the backend also returns the refresh token in the response body. The frontend stores it in `sessionStorage` and re-sends it when the cookie path fails (Brave Shields, Safari ITP).

`sessionStorage` survives page reloads but clears on tab close. In local development, `SameSite=Lax; Secure=False` is used (same-origin via Docker Compose / Nginx).

---

## What I Would Add With More Time

- **Celery + Redis** for async tasks (low-stock alert emails, scheduled expiry notifications)
- **Product images** via S3
- **Date range filtering** on financial reports and order lists
- **CSV export** for stock, orders, and financial summaries
- **Webhook delivery logs** — persist incoming integration events for debugging
- **OAuth callback UI** — in-app flow to connect QuickBooks/NetSuite without manual env var setup
- **Audit log** on user and organization management actions (admin operations currently have no trail)
