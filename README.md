# Kaizntree Inventory Management System

A full-stack inventory management platform for F&B CPG brands, built as a take-home
challenge for Kaizntree.

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

### Inventory & Products
- Full CRUD for products with SKU, unit type, description, and per-user uniqueness enforcement
- **Minimum stock threshold** — set a floor quantity per product; the product list highlights any product whose stock has fallen below it
- **Bulk CSV import** — upload a CSV file to create multiple products at once, with per-row Zod validation, live status badges, and a downloadable sample template

### Stock Management
- Track stock entries per product with lot identifier, quantity, and notes
- **Expiry date tracking** — optional expiry date per stock entry; the dashboard surfaces entries expiring within 30 days

### Dashboard
- **Financial summary** — total cost, revenue, gross profit, and margin derived from confirmed orders in a single ORM annotation query
- **Order pipeline** — counts of draft/confirmed/cancelled purchase and sales orders
- **Low-stock alerts** — table of products currently below their minimum threshold, with a direct link to each product
- **Expiring stock** — table of stock entries expiring within 30 days, sorted by closest expiry
- **Revenue vs. cost bar chart** — per-product comparison powered by Mantine Charts
- **Ring progress** — visual profit margin indicator

### Orders
- Purchase Orders: create → confirm (creates/increments stock) → cancel
- Sales Orders: create → confirm (validates and decrements stock) → cancel (restores stock if was confirmed)
- All mutations run in `transaction.atomic()` with `select_for_update()` to prevent race conditions

### Financials
- Per-product and aggregate profit/margin reporting, always computed live from confirmed orders — no denormalized storage

## Project Structure

```
kaizntree-challenge/
├── backend/
│   ├── apps/
│   │   ├── users/        # Custom User model, JWT auth endpoints
│   │   ├── inventory/    # Product + Stock models, CRUD API
│   │   │   └── migrations/
│   │   │       ├── 0001_initial.py
│   │   │       ├── 0002_product_min_stock_quantity.py
│   │   │       └── 0003_stock_expiry_date.py
│   │   ├── orders/       # PurchaseOrder + SalesOrder with confirm/cancel
│   │   └── financials/   # Profit/margin computation, reporting endpoints
│   └── kaizntree/        # Django project (settings split: base/dev/prod)
└── frontend/
    └── src/
        ├── api/           # Axios client + per-resource API functions
        ├── store/         # Zustand auth store (in-memory access token)
        ├── pages/         # Route-level page components
        │   └── products/
        │       └── ImportProductsModal.tsx  # CSV bulk import UI
        ├── utils/
        │   ├── csvParser.ts     # RFC-4180-compliant CSV parser (no dependencies)
        │   └── formatters.ts    # Currency and percent formatters
        └── types/         # TypeScript interfaces mirroring API shapes
```

## Architecture Decisions

### Authentication: Hybrid httpOnly Cookie + In-Memory Access Token

Rather than storing JWTs in `localStorage` (vulnerable to XSS), the app uses:

- **Access token** (15 min TTL) — stored in Zustand (memory only). Never touches `localStorage` or the DOM. Sent as `Authorization: Bearer` on every request.
- **Refresh token** (7 days) — stored in two places for resilience:
  - An `httpOnly; SameSite=Lax; Secure` cookie (primary — invisible to JavaScript, works when the Vercel proxy forwards Set-Cookie headers).
  - `sessionStorage["kz_refresh_token"]` (fallback — survives page reloads, cleared on tab close, used when cookies are blocked by Brave Shields / Safari ITP).

The Axios client has a response interceptor: on any 401, it transparently calls `/auth/refresh/`, updates the in-memory token, and retries the original request. On hard page refresh, the app calls `POST /auth/refresh/` on mount — it tries the httpOnly cookie first, then falls back to the `sessionStorage` copy sent in the request body. Either path silently restores the session without re-login.

> **Note:** The `/auth/refresh/` view reads the token from the cookie and injects it
> into the request via `request._full_data` (the backing store for DRF's read-only
> `Request.data` property) before delegating to `TokenRefreshView`.

### Data Isolation via `OwnedModelMixin`

All ViewSets extend a single `OwnedModelMixin` that filters every queryset to `owner=request.user`. Because `get_object()` calls `get_queryset()` first, cross-user access always returns **404**, not 403 — this avoids leaking the existence of other users' resources.

### Transactional Stock Mutations

Confirming or cancelling orders modifies stock quantities. Both operations run in `transaction.atomic()` with `select_for_update()` to prevent race conditions under concurrent requests. Stock quantities are incremented using a DB-level `F("quantity") + delta` expression — no read-modify-write pattern.

### Financial Computation: Single ORM Query, No Denormalization

All profit/margin metrics are computed at query time via a single annotated queryset using Django's `Sum`, `F`, and `ExpressionWrapper`. No financial data is stored — it's always derived from confirmed orders. This means the dashboard is always accurate, never stale.

### SKU Uniqueness Per User

SKU uniqueness is enforced at two levels: a `validate_sku` check in the serializer (returns a clean 400) and a `unique_together = [("owner", "sku")]` DB constraint as a safety net. Two different users can use the same SKU; a user cannot have two products with the same SKU.

### CSV Import: Zero-Dependency Parser

Rather than pulling in a CSV library, `frontend/src/utils/csvParser.ts` implements an RFC-4180-compliant parser that handles quoted fields, escaped quotes, Windows/Unix line endings, and unknown column ordering. Each row is validated client-side with Zod before being submitted, and rows are imported sequentially so partial failures are recoverable without re-uploading the whole file.

## Cloud Deployment

The app is deployed as two independent services: Railway hosts the Django backend + PostgreSQL database; Vercel hosts the React SPA.

### Backend — Railway

`railway.toml` (repo root) tells Railway to build from the backend `Dockerfile` (production stage), healthcheck at `GET /health`, and restart on failure.

The production Dockerfile stage runs `collectstatic` at build time and starts Gunicorn bound to `$PORT` (injected by Railway at runtime). `entrypoint.sh` waits for PostgreSQL to be ready using `pg_isready` against the `DATABASE_URL` Railway provides automatically when the PostgreSQL plugin is added.

**Required Railway environment variables:**

| Variable | Value |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `kaizntree.settings.production` |
| `DJANGO_SECRET_KEY` | long random string |
| `CORS_ALLOWED_ORIGINS` | `https://kaizntree-challenge.vercel.app` |
| `DATABASE_URL` | *(auto-injected by Railway — add the PostgreSQL plugin)* |

> `DJANGO_ALLOWED_HOSTS` does **not** need to be set — `production.py` already allows all `*.railway.app` / `*.up.railway.app` patterns plus any custom domain in `RAILWAY_PUBLIC_DOMAIN`.

### Frontend — Vercel

Point Vercel at the `frontend/` subdirectory with build command `npm run build` and output directory `dist`. `frontend/vercel.json` rewrites every route to `index.html` for client-side SPA routing.

**Required Vercel environment variable:**

| Variable | Value |
|---|---|
| `VITE_API_URL` | `https://kaizntree-challenge-production.up.railway.app` |

### Cross-Domain Session Architecture

Because Vercel and Railway are on different domains, the session-persistence strategy is dual-layered:

1. **httpOnly cookie** (`SameSite=None; Secure`) — set by Railway on every login/refresh. Works in browsers that allow cross-domain cookies (Chrome, Firefox default). Automatically sent by the browser on subsequent refresh calls.

2. **`sessionStorage["kz_refresh_token"]`** — the backend also returns the refresh token in the response body. The frontend stores it in `sessionStorage` on login and re-sends it in the request body when the cookie path fails. This covers Brave (Shields on), Safari (ITP), and any browser where cross-domain cookies are blocked.

`sessionStorage` survives page reloads but is cleared when the tab closes. In local development, `SameSite=Lax; Secure=False` is used (same-origin via Docker Compose / Nginx).

## API Reference

Interactive docs available at `/api/schema/swagger-ui/` when the backend is running.

### Endpoints Summary

**Auth** — `/api/v1/auth/`
- `POST /register/` — create account, returns access token + sets refresh cookie
- `POST /login/` — authenticate, returns access token + sets refresh cookie
- `POST /refresh/` — exchange refresh cookie for new access token
- `POST /logout/` — blacklist refresh token
- `GET /me/` — current user info

**Products** — `/api/v1/products/`
- Full CRUD + search (`?search=`) + filter (`?unit_type=`)
- `GET /{id}/stock/` — stock entries for this product
- `GET /{id}/financials/` — per-product profit/margin

**Stock** — `/api/v1/stock/`
- Full CRUD + filter by product
- Fields include `expiry_date` (optional, ISO date)

**Purchase Orders** — `/api/v1/purchase-orders/`
- Full CRUD (only drafts can be edited/deleted)
- `POST /{id}/confirm/` — creates/increments stock, transitions to confirmed
- `POST /{id}/cancel/`

**Sales Orders** — `/api/v1/sales-orders/`
- Full CRUD (only drafts can be edited/deleted)
- `POST /{id}/confirm/` — decrements stock (validates sufficiency)
- `POST /{id}/cancel/` — restores stock if was confirmed

**Financials** — `/api/v1/financials/`
- `GET /summary/` — total cost, revenue, profit, margin across all products
- `GET /products/` — per-product breakdown

## What I Would Add With More Time

- **Celery + Redis** for async tasks (low-stock alert emails, scheduled expiry notifications)
- **Product images** via S3
- **Role-based access** — owner vs. read-only collaborator on the same account
- **Audit log** on order status transitions
- **Date range filtering** on financial reports
- **CSV export** for stock and orders
