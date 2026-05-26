# Kaizntree Inventory Management System

A full-stack inventory management platform for F&B CPG brands — built as a take-home challenge for Kaizntree.

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
| Backend | Python 3.12, Django 5.1, Django REST Framework |
| Auth | djangorestframework-simplejwt |
| API Docs | drf-spectacular (OpenAPI / Swagger UI) |
| Frontend | React 18, TypeScript, Vite, Mantine 7, TanStack Query v5, Tailwind CSS |
| Infra | Docker Compose, PostgreSQL 16, Nginx |
| Tests | pytest-django, factory-boy, pytest-cov |
| CI | GitHub Actions (pytest + tsc) |

## Project Structure

```
kaizntree-challenge/
├── backend/
│   ├── apps/
│   │   ├── users/        # Custom User model, JWT auth endpoints
│   │   ├── inventory/    # Product + Stock models, CRUD API
│   │   ├── orders/       # PurchaseOrder + SalesOrder with confirm/cancel
│   │   └── financials/   # Profit/margin computation, reporting endpoints
│   └── kaizntree/        # Django project (settings split: base/dev/prod)
└── frontend/
    └── src/
        ├── api/           # Axios client + per-resource API functions
        ├── store/         # Zustand auth store (in-memory access token)
        ├── pages/         # Route-level page components
        └── types/         # TypeScript interfaces mirroring API shapes
```

## Architecture Decisions

### Authentication: Hybrid httpOnly Cookie + In-Memory Access Token

Rather than storing JWTs in `localStorage` (vulnerable to XSS), the app uses:

- **Access token** (15 min TTL) — stored in Zustand (memory only). Never touches `localStorage` or the DOM. Sent as `Authorization: Bearer` on every request.
- **Refresh token** (7 days) — stored in a `httpOnly; SameSite=Lax` cookie, invisible to JavaScript. Sent automatically by the browser on refresh calls.

The Axios client has a response interceptor: on any 401, it transparently calls `/auth/refresh/`, updates the in-memory token, and retries the original request. On hard page refresh, the app calls `GET /auth/me/` on mount — if the refresh cookie is still valid, the session is silently restored without re-login.

### Data Isolation via `OwnedModelMixin`

All ViewSets extend a single `OwnedModelMixin` that filters every queryset to `owner=request.user`. Because `get_object()` calls `get_queryset()` first, cross-user access always returns **404**, not 403 — this avoids leaking the existence of other users' resources.

### Transactional Stock Mutations

Confirming or cancelling orders modifies stock quantities. Both operations run in `transaction.atomic()` with `select_for_update()` to prevent race conditions under concurrent requests. Stock quantities are incremented using a DB-level `F("quantity") + delta` expression — no read-modify-write pattern.

### Financial Computation: Single ORM Query, No Denormalization

All profit/margin metrics are computed at query time via a single annotated queryset using Django's `Sum`, `F`, and `ExpressionWrapper`. No financial data is stored — it's always derived from confirmed orders. This means the dashboard is always accurate, never stale.

### SKU Uniqueness Per User

SKU uniqueness is enforced at the database level with `unique_together = [("owner", "sku")]`. Two different users can use the same SKU for their own products, but a user cannot have two products with the same SKU.

## API Reference

Interactive API docs are available at `/api/schema/swagger-ui/` when the backend is running.

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

- **Celery + Redis** for async tasks (low-stock alert emails, bulk CSV exports)
- **Product images** via S3
- **Role-based access** — owner vs. read-only collaborator on the same account
- **Audit log** on order status transitions
- **Cloud deployment** (Railway for backend + db, Vercel for frontend)
- **Date range filtering** on financial reports
