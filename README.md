# MultiVendor Hub

A multi-tenant e-commerce SaaS platform: any seller can spin up their own storefront (own catalog, theme, domain, subscription plan) on shared infrastructure, plus a cross-store marketplace where shoppers can buy from several vendors in a single checkout.

**Stack:** FastAPI (Python 3.12) + SQLAlchemy 2.0 (async) + MySQL 8 + Redis, Next.js 16 (React 19, App Router) + TypeScript + Tailwind, Docker + Caddy for deployment.

## What it does

- **Multi-tenant storefronts** — each seller (`tenant`) gets an isolated catalog, theme, and admin dashboard under its own slug (`/store/{slug}`), with a real custom-domain option: point a seller's own domain at the server and Caddy + the Next.js proxy serve their store from it automatically (see `server/app/routers/domain_router.py`, `frontend/src/proxy.ts`, `Caddyfile`).
- **Row-level tenant isolation** — every tenant-scoped table carries a `tenant_id`; access is enforced at the query layer, not just the UI (see `tests/test_tenant_isolation_rls.py`).
- **Catalog & inventory** — products with variants, images, reviews, digital goods (no shipping/stock tracking), and bundles.
- **Cart & checkout with real concurrency control** — Redis distributed locks (`lock:tenant:{id}:variant:{id}`) prevent overselling under concurrent checkouts.
- **Cross-store marketplace checkout** — a single cart spanning multiple vendors is split into a `MasterOrder` with per-tenant sub-orders and a commission/payout split.
- **Subscriptions & plan limits** — product/storage caps enforced server-side, with a real "upgrade your plan" UI when a seller hits its limit (403).
- **Payments** — pluggable provider: `mock` (instant-pay, zero external calls, default for local dev) or `stripe` (real PaymentIntents + webhook confirmation).
- **Shipping** — Israeli courier integration (HFD, LionWheel) via a vendored SDK (`packages/israel-shipping-sdk`), with per-tenant encrypted credentials and optional auto-fulfillment.
- **AI CMS copilot** — a Gemini-backed assistant that can edit storefront pages/products for a seller, with irreversible actions gated behind an explicit human confirmation step (`AIPendingAction`).
- **i18n / RTL** — product and page content stored as JSON per-locale; storefront UI toggles `dir="rtl"`/`"ltr"`.
- **Super admin** — platform-wide tenant management, audit log, storefront template catalog.
- **Auth** — JWT-based, with per-store role membership (`UserStoreMembership`: `tenant_admin` / `customer`), password reset via transactional email, and a signed-cookie session that Next.js's proxy layer verifies (HMAC, not just decoded) before allowing `/admin`, `/super-admin`, `/crm` routes through.
- **Object storage** — pluggable: local disk (default, zero setup) or any S3-compatible bucket (AWS S3, Cloudflare R2, Backblaze B2) behind `STORAGE_TYPE=s3` (see `app/services/storage_service.py`).
- **Error tracking** — optional Sentry integration (`SENTRY_DSN`), a no-op with zero external calls until set (see `app/core/observability.py`).

## Project layout

```
server/            FastAPI backend
  app/
    routers/       HTTP endpoints, grouped by domain (auth, storefront, tenant_admin, marketplace, ai, ...)
    services/      business logic (checkout, catalog, shipping, payments, AI tools, ...)
    models/        SQLAlchemy models
    schemas/       Pydantic request/response schemas
    core/          config, security, rate limiting
  alembic/         DB migrations
  tests/           (see also root-level tests/, below)

frontend/          Next.js app
  src/
    app/           routes: storefront, admin (CMS), super-admin, checkout, account, marketplace, auth
    components/    shared UI
    lib/           API client, cart, AI tool types
    proxy.ts       Next.js proxy: verifies the session JWT signature before admin/super-admin/crm routes
  e2e/             Playwright end-to-end specs

packages/
  israel-shipping-sdk/   standalone courier-integration SDK, vendored in as an editable install

docs/
  erd.md                 database schema reference (entity list + relationships)
  QA_AUDIT_REPORT.md      point-in-time QA audit (test coverage, bugs found & fixed)

tests/              backend test suite (pytest, 300+ tests)
db/                 raw SQL schema/seed reference
```

## Running locally

**Backend**

```bash
docker compose up -d          # MySQL + Redis only
cd server
pip install -r requirements.txt
cp ../.env.example .env       # then fill in server/.env — see below
alembic upgrade head
python seed_db.py             # creates a demo tenant + data
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env.local    # JWT_SECRET_KEY must match the backend's SECRET_KEY
npm run dev
```

Backend runs on `:8000` (Swagger UI at `/docs`), frontend on `:3000`.

## Environment configuration

Local dev only needs MySQL + Redis (`docker-compose.yml`) plus a `.env` — everything else (payments, email, AI, shipping) defaults to a safe mock/disabled mode with zero external calls, so the app runs fully offline out of the box. See `.env.example` for the full list and what switching each one to "real" requires (Stripe keys, SMTP credentials, a Gemini API key, a Fernet encryption key for courier credentials).

## Testing

```bash
# Backend (pytest, targets a separate multivendor_test DB — see tests/conftest.py)
python -m pytest tests/ -q

# Frontend unit/integration
cd frontend && npx vitest run

# Frontend typecheck
cd frontend && npx tsc --noEmit

# E2E (requires backend on :8000 and frontend on :3000, seeded via server/seed_db.py)
cd frontend && npx playwright test
```

CI (`.github/workflows/ci.yml`) runs backend migrations + pytest, and frontend typecheck + unit tests + build, on every push/PR to `main`.

## Deployment

`docker-compose.prod.yml` brings up the full stack (MySQL, Redis, backend, frontend, and Caddy for automatic TLS via Let's Encrypt) behind two domains (`APP_DOMAIN`, `API_DOMAIN`). Copy `.env.example` to `.env`, fill it in, then:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

See the comments in `.env.example`, `Caddyfile`, and `docker-compose.prod.yml` for what's required vs. optional at each stage.

**Backups:** `deploy/backup_db.sh` dumps the production MySQL DB (gzip, pruned after `BACKUP_RETENTION_DAYS`, default 14) — run it on the VPS via cron:

```bash
0 3 * * * cd /path/to/MultiVendor && ./deploy/backup_db.sh >> /var/log/multivendor-backup.log 2>&1
```

`deploy/restore_db.sh <dump.sql.gz>` restores one back (destructive; asks for confirmation).

## Known gaps / not yet production-ready

- No load testing has been done against the Redis-lock checkout path.
- No CD — CI (`.github/workflows/ci.yml`) tests and builds on every push, but deploying to the VPS is still a manual `git pull && docker compose ... up -d --build`.
- Secrets live in a plain `.env` on the VPS, not a secret manager — reasonable for a course/small deployment, not for a team-scale one.
