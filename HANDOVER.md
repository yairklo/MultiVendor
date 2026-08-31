# Project Status

Last updated: 2026-08-31.

## Current state

The platform is feature-complete for a multi-tenant storefront + marketplace demo: auth/RBAC, tenant admin CMS, catalog/cart/checkout with Redis-locked concurrency control, subscriptions with enforced plan limits, an AI CMS copilot, i18n/RTL, Israeli shipping integration, and Stripe-ready payments (mock by default). See [README.md](README.md) for the full feature list and how to run it.

Test suite, as of this update:

| Suite | Count | Status |
|---|---|---|
| Backend (`pytest`) | 312 test functions | Green in CI on every push/PR |
| Frontend unit/integration (`vitest`) | 82 tests | Green (verified locally) |
| Frontend typecheck (`tsc --noEmit`) | — | Clean, 0 errors |
| Frontend lint (`eslint`) | — | 0 errors, 6 minor warnings (non-blocking) |
| E2E (`playwright`) | 11 spec files | Covered in CI history; see `docs/QA_AUDIT_REPORT.md` for the audit that established this baseline |

The database-isolation issue this file used to describe (test runs corrupting the dev DB via `IntegrityError`/duplicate entries) is resolved: `tests/conftest.py` now points the whole test run at a separate `multivendor_test` database, distinct from `multivendor_dev`, before `app.main` is even imported. `docker-compose.yml` (dev) and `.github/workflows/ci.yml` both reflect this split.

## Known gaps

See the "Known gaps / not yet production-ready" section in [README.md](README.md) — no error tracking, no automated DB backups, local-disk file storage, per-tenant custom domains not yet wired into Caddy's TLS termination, no load testing on the checkout path.

## Where things live

- Architecture, running locally, testing, deployment: [README.md](README.md)
- Database schema reference: [docs/erd.md](docs/erd.md)
- Point-in-time QA audit (what was tested, what bugs were found and fixed): [docs/QA_AUDIT_REPORT.md](docs/QA_AUDIT_REPORT.md)
