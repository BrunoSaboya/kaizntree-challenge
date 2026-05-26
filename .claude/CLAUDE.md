# kaizntree-challenge

Full-stack inventory management system built as a take-home interview challenge
for Kaizntree (AI-powered CPG inventory ops startup).

## Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.12, Django 5.1, Django REST Framework 3.15 |
| Auth | djangorestframework-simplejwt — httpOnly refresh cookie + in-memory access token |
| API docs | drf-spectacular → Swagger UI at `/api/schema/swagger-ui/` |
| DB | PostgreSQL 16 |
| Frontend | React 18, TypeScript 5, Vite 5, Mantine 7, TanStack Query v5, Zustand, Zod |
| Infra | Docker Compose (multi-stage Dockerfiles), Nginx SPA proxy |
| Tests | pytest-django, factory-boy, freezegun |
| CI | GitHub Actions (`.github/workflows/ci.yml`) |

## Running the project

```bash
cp .env.example .env
docker compose up --build
```

- Frontend (dev Vite): `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/api/schema/swagger-ui/`

Backend tests:
```bash
docker compose run --rm backend pytest
```

## Key file paths

```
backend/
  kaizntree/settings/
    base.py            # all shared config (JWT, DRF, CORS, SIMPLE_JWT cookie keys)
    development.py     # DEBUG=True, AUTH_COOKIE_SECURE=False
    production.py      # AUTH_COOKIE_SECURE=True, SameSite=Strict
  apps/
    users/             # custom User model (email as USERNAME_FIELD), JWT auth views
    inventory/         # Product + Stock models, OwnedModelMixin, ProductViewSet
    orders/            # PurchaseOrder + SalesOrder, confirm/cancel service layer
    financials/        # single-query ORM annotation for profit/margin reporting
  entrypoint.sh        # waits for pg_isready → migrate → exec

frontend/src/
  api/client.ts        # Axios instance + 401 interceptor (NO window.location.href redirect)
  store/authStore.ts   # Zustand: in-memory access token + user
  App.tsx              # session restore on mount (calls /auth/me/ then /auth/refresh/)
  pages/               # auth, dashboard, products, stock, purchase-orders, sales-orders
  components/layout/AppShellLayout.tsx  # Mantine AppShell, navbar, user menu
  main.tsx             # MantineProvider with custom brand theme
```

## Architecture decisions

### Auth
- Access token (15 min): stored in Zustand memory only — never localStorage/DOM
- Refresh token (7 days): httpOnly cookie (`SameSite=Lax` dev, `Strict` prod)
- 401 interceptor: on 401 → try `/auth/refresh/` → update Zustand, retry request
- On page load: `GET /auth/me/` + `POST /auth/refresh/` to restore session from cookie
- **Do NOT add `window.location.href` back to the 401 interceptor** — causes infinite reload loop on page load since ProtectedRoute already handles unauthenticated routing via React Router

### Data isolation
`OwnedModelMixin` (defined in `apps/inventory/views.py`) filters every queryset by
`owner=request.user` and returns 404 (not 403) for cross-user access.
All ViewSets extend this mixin.

### Stock mutations (transactional)
`apps/orders/services.py` — all confirm/cancel operations use `select_for_update()`
inside `transaction.atomic()`. Stock quantity updated via DB-level arithmetic (`F()`
expressions) to prevent race conditions under concurrent requests.

### Financial computation
`apps/financials/services.py` — single ORM annotation query (no N+1, no denormalization):
```python
Product.objects.filter(owner=user).annotate(
    total_cost=Sum(F("purchase_orders__quantity") * F("purchase_orders__cost_per_unit"),
                   filter=Q(purchase_orders__status="confirmed"), default=Decimal("0")),
    total_revenue=Sum(..., filter=Q(sales_orders__status="confirmed"), default=Decimal("0")),
    ...
)
```

### SKU uniqueness
Enforced at both serializer level (`validate_sku` in `inventory/serializers.py`) and
DB level (`unique_together = [("owner", "sku")]`). Serializer check runs first → user
gets a clean 400, not a raw IntegrityError.

## API base path

`/api/v1/` — all endpoints prefixed here.

Key endpoints:
- `POST /auth/register/`, `POST /auth/login/`, `POST /auth/refresh/`, `POST /auth/logout/`, `GET /auth/me/`
- `GET/POST /products/`, `GET/PATCH/DELETE /products/{id}/`
- `POST /purchase-orders/{id}/confirm/` — creates/increments Stock, transitions to CONFIRMED
- `POST /sales-orders/{id}/confirm/` — validates stock sufficiency, decrements, transitions to CONFIRMED
- `POST /purchase-orders/{id}/cancel/`, `POST /sales-orders/{id}/cancel/` — cancel; confirmed SO restores stock
- `GET /financials/summary/`, `GET /financials/products/`

## Theme / colors

Custom Mantine theme in `frontend/src/main.tsx`:
- `primaryColor: "brand"` — 10-shade palette derived from `#002c10` (dark forest green)
- App background: `#fcf6ef` (warm cream) — body, AppShell header/navbar/main, auth pages
- Cards, Paper, Tables: white (intentionally kept white for contrast)

## Dev proxy (Docker)

Vite proxy in `vite.config.ts` reads `process.env.VITE_API_URL || "http://localhost:8000"`.
`docker-compose.override.yml` sets `VITE_API_URL=http://backend:8000`.
**Do not change this back to a hardcoded `http://localhost:8000`** — that URL resolves to
the frontend container itself inside Docker, not the backend service.

## Test factories

- `apps/inventory/tests/factories.py` — `UserFactory`, `ProductFactory`, `StockFactory`
- `apps/orders/tests/factories.py` — `PurchaseOrderFactory`, `SalesOrderFactory`
- `SalesOrderFactory` has a default `stock` SubFactory; pass `stock=instance` explicitly
  when you need a specific stock entry
- When confirming a PO in tests, always capture the return value:
  `po = confirm_purchase_order(po, "LOT-1")` — the returned PO has `stock` populated;
  the original object does not

## Migrations

All migration files committed. Each app has a single `0001_initial.py`:
- `apps/users/migrations/` — custom User model, depends on `auth.0012`
- `apps/inventory/migrations/` — Product + Stock, depends on `users.0001`
- `apps/orders/migrations/` — PurchaseOrder + SalesOrder, depends on `inventory.0001`

`simplejwt.token_blacklist` migrations applied automatically via `migrate --noinput` in
`entrypoint.sh` — no manual step needed.
