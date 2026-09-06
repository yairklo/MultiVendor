# Deploying the whole stack on one VPS via Coolify

No Vercel — frontend, backend, MySQL, Redis and Caddy all run on your VPS,
managed by Coolify. This keeps the tenant custom-domain feature (Caddy's
on-demand TLS) working exactly as designed, since it already assumes
frontend+backend+Caddy live together (`docker-compose.prod.yaml`, `Caddyfile`).

No code changes were needed for this — the existing prod compose file already
does what Coolify needs. This is a deployment runbook, not a code change.

## 0. Why you must disable Coolify's built-in proxy first

Coolify runs its own reverse proxy (Traefik) bound to host ports 80/443 by
default. Our stack's `caddy` service also needs 80/443 — both to serve
`APP_DOMAIN`/`API_DOMAIN` and, critically, to complete Let's Encrypt's
HTTP-01/TLS-ALPN-01 challenges for **on-demand** tenant custom domains. Those
challenges are validated by Let's Encrypt hitting port 80 or 443 as seen from
the public internet — if Caddy were moved to some other port instead, cert
issuance would silently stop working for both the main domains and every
tenant custom domain. So the two proxies can't coexist on 80/443; Coolify's
has to step aside.

**Coolify dashboard → your Server → "Proxy" tab → Stop the proxy** (or set
type to "None"). This does **not** affect the Coolify dashboard/API itself —
that runs on its own port (default 8000) and keeps working. It only stops
Coolify from fronting *applications* on 80/443, which our own Caddy now owns
instead.

## 1. Pick your domains (no DNS purchase needed yet)

Use [sslip.io](https://sslip.io) — a wildcard DNS service with no signup:
`anything.<your-vps-ip-with-dashes>.sslip.io` resolves to `<your-vps-ip>`
automatically. It's a real, publicly-resolvable hostname, so Caddy's
automatic HTTPS works with it exactly as it would with a bought domain —
this is not an insecure workaround, just a free stand-in for DNS until you
buy a real domain later (at which point you only change `APP_DOMAIN`/
`API_DOMAIN` and redeploy — nothing else changes).

If your VPS IP is e.g. `203.0.113.10`, use:

```
APP_DOMAIN=app.203-0-113-10.sslip.io
API_DOMAIN=api.203-0-113-10.sslip.io
```

(Swap in your real VPS IP with dots replaced by dashes.)

## 2. Generate secrets

Run these once, keep the output for step 4:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"                 # SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(24))"                 # DB_ROOT_PASSWORD
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # SHIPPING_CREDENTIALS_ENCRYPTION_KEY (optional — only if you'll use the courier integration)
```

## 3. Create the Coolify resource

1. Coolify → Project → **+ New Resource → Docker Compose**.
2. Point it at this git repo, branch `main`, compose file path
   `docker-compose.prod.yaml` (repo root — the build contexts inside it
   already reference `server/Dockerfile` and `frontend/Dockerfile` relative
   to the repo root, so don't change the working directory).
3. Do **not** let Coolify auto-inject domains/proxy labels for these
   services — we're using our own Caddy (already stopped Coolify's proxy in
   step 0), so leave Coolify's "Domains" fields for this resource empty.

## 4. Set environment variables (in Coolify's resource → Environment Variables)

| Variable | Value |
|---|---|
| `APP_DOMAIN` | `app.<ip-with-dashes>.sslip.io` |
| `API_DOMAIN` | `api.<ip-with-dashes>.sslip.io` |
| `ACME_EMAIL` | a real email you control (Let's Encrypt expiry notices) |
| `DB_ROOT_PASSWORD` | generated in step 2 |
| `DB_NAME` | `multivendor_prod` |
| `SECRET_KEY` | generated in step 2 |
| `EMAIL_PROVIDER` | `console` (fine for go-live; logs reset emails instead of sending — switch to `smtp` + fill `SMTP_*` once you have real SMTP credentials) |
| `PAYMENT_PROVIDER` | `mock` (fine for go-live — switch to `stripe` + fill `STRIPE_*` once ready to take real payments) |
| `SHIPPING_CREDENTIALS_ENCRYPTION_KEY` | generated in step 2, or leave blank to keep the courier integration disabled |
| `GEMINI_API_KEY`, `SENTRY_DSN` | leave blank for now — both are no-op/disabled when unset |
| `STORAGE_TYPE` | `local` (fine to start; uploads persist in the `uploads` docker volume) |

Everything left blank above degrades to a safe disabled/mock mode — see
`.env.example` at the repo root for the full reference and what each one
unlocks.

## 5. Deploy

Click Deploy in Coolify. It builds `server/Dockerfile` and
`frontend/Dockerfile`, brings up `mysql`, `redis`, `backend`, `frontend`,
`caddy`, and Caddy requests real Let's Encrypt certs for both domains on
first request (may take ~10-30s the very first time each hostname is hit).

## 6. Run migrations + seed data (one-time, after first deploy)

Exec into the `backend` container from Coolify's UI (or SSH + `docker exec`)
and run:

```bash
alembic upgrade head
python seed_db.py   # optional — creates a demo tenant + sample data
```

## 7. Verify

```bash
curl -I https://api.<ip-with-dashes>.sslip.io/health
curl -I https://app.<ip-with-dashes>.sslip.io
```

Both should return `200`/`30x` with a valid TLS handshake (no `-k` needed).
Then open `https://app.<ip-with-dashes>.sslip.io` in a browser, sign up, and
confirm login/checkout/admin all work end to end.

To confirm the on-demand tenant-domain path still works: set a tenant's
`custom_domain` (via `/admin` store settings) to another sslip.io hostname
pointing at the same IP (e.g. `myshop.<ip-with-dashes>.sslip.io`) and load
it — Caddy should issue it a cert on first hit and route to that tenant's
storefront.

## 8. Backups

Coolify won't do this for you. Set up the existing backup script as a cron
job on the VPS itself (outside Coolify):

```
0 3 * * * cd /path/to/MultiVendor && ./deploy/backup_db.sh >> /var/log/multivendor-backup.log 2>&1
```

## 9. Moving to a real domain later

Buy a domain, point an A record at the VPS IP, then just change
`APP_DOMAIN`/`API_DOMAIN` in Coolify's env vars to the real hostnames and
redeploy — Caddy issues fresh certs for the new hostnames automatically,
nothing else in the stack needs to change.
