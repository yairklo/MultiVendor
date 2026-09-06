# Deploying the whole stack on one VPS via Coolify (shared with other apps)

No Vercel — frontend, backend, MySQL and Redis all run on your VPS, managed
by Coolify, **alongside other apps already deployed there**. Because other
apps depend on Coolify's own shared proxy (Traefik) for their public
domains, this stack does **not** bring its own Caddy the way
`docker-compose.prod.yaml` (the single-dedicated-VPS variant, see the main
[README](../README.md#deployment)) does — stopping/replacing that shared
proxy would take those other apps offline too. Use
`docker-compose.coolify.yaml` instead, which drops the `caddy` service
entirely and lets Coolify's existing proxy handle TLS for this app's two
domains the same way it already does for everything else on the server.

## The tradeoff this implies

`docker-compose.prod.yaml`'s Caddy setup issues certificates **on demand**
for arbitrary tenant custom domains (a seller points their own domain at the
server and it just works, no admin action needed) — that relies on Caddy
alone owning ports 80/443 so it can answer Let's Encrypt's ACME challenge
for any hostname. Coolify's shared Traefik doesn't do that: it only manages
TLS for domains you explicitly register per application in its UI. So on a
shared VPS, a seller's custom domain becomes a **manual step**: an admin
adds the domain to the `frontend` app in Coolify's UI when a seller sets one
in their store settings, and Coolify issues it a cert the same way it does
for `APP_DOMAIN`/`API_DOMAIN` below. Still same-day, just not zero-touch —
if that manual step becomes a real bottleneck later, it can be automated by
calling Coolify's API from `server/app/routers/domain_router.py` when a
tenant's `custom_domain` is set (not done here — real engineering work of
its own, only worth it once there's an actual queue of tenants waiting).

## 1. Pick your domains (no DNS purchase needed yet)

Use [sslip.io](https://sslip.io) — a wildcard DNS service with no signup:
`anything.<your-vps-ip-with-dashes>.sslip.io` resolves to `<your-vps-ip>`
automatically. It's a real, publicly-resolvable hostname, so Coolify's
automatic HTTPS works with it exactly as it would with a bought domain —
this is not an insecure workaround, just a free stand-in for DNS until you
buy a real domain later (at which point you just re-point the domain in
Coolify's UI — nothing else in the stack changes).

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
   `docker-compose.coolify.yaml` (repo root — the build contexts inside it
   already reference `server/Dockerfile` and `frontend/Dockerfile` relative
   to the repo root, so don't change the working directory).
3. Do **not** touch the server's global Proxy settings — leave Coolify's
   shared proxy exactly as it is for your other apps.

## 4. Assign domains to the two services

In the Coolify resource, open the `backend` service and set its domain to
`API_DOMAIN` (e.g. `api.<ip-with-dashes>.sslip.io`); open `frontend` and set
its domain to `APP_DOMAIN` (e.g. `app.<ip-with-dashes>.sslip.io`). Coolify
issues each a Let's Encrypt cert through its existing shared proxy — no
change to how your other apps on this server are routed.

## 5. Set environment variables (in Coolify's resource → Environment Variables)

| Variable | Value |
|---|---|
| `APP_DOMAIN` | `app.<ip-with-dashes>.sslip.io` — must match what you set on `frontend` in step 4 |
| `API_DOMAIN` | `api.<ip-with-dashes>.sslip.io` — must match what you set on `backend` in step 4 |
| `DB_ROOT_PASSWORD` | generated in step 2 |
| `DB_NAME` | `multivendor_prod` |
| `SECRET_KEY` | generated in step 2 |
| `EMAIL_PROVIDER` | `console` (fine for go-live; logs reset emails instead of sending — switch to `smtp` + fill `SMTP_*` once you have real SMTP credentials) |
| `PAYMENT_PROVIDER` | `mock` (fine for go-live — switch to `stripe` + fill `STRIPE_*` once ready to take real payments) |
| `SHIPPING_CREDENTIALS_ENCRYPTION_KEY` | generated in step 2, or leave blank to keep the courier integration disabled |
| `GEMINI_API_KEY`, `SENTRY_DSN` | leave blank for now — both are no-op/disabled when unset |
| `STORAGE_TYPE` | `local` (fine to start; uploads persist in the `uploads` docker volume) |

`ACME_EMAIL` is not needed here — that was only for Caddy. Coolify already
has its own ACME email configured server-wide for its shared proxy.

Everything left blank above degrades to a safe disabled/mock mode — see
`.env.example` at the repo root for the full reference and what each one
unlocks.

## 6. Deploy

Click Deploy in Coolify. It builds `server/Dockerfile` and
`frontend/Dockerfile`, brings up `mysql`, `redis`, `backend`, `frontend`,
and the shared proxy requests real Let's Encrypt certs for both domains on
first request (may take ~10-30s the very first time each hostname is hit).

## 7. Run migrations + seed data (one-time, after first deploy)

Exec into the `backend` container from Coolify's UI (or SSH + `docker exec`)
and run:

```bash
alembic upgrade head
python seed_db.py   # optional — creates a demo tenant + sample data
```

## 8. Verify

```bash
curl -I https://api.<ip-with-dashes>.sslip.io/health
curl -I https://app.<ip-with-dashes>.sslip.io
```

Both should return `200`/`30x` with a valid TLS handshake (no `-k` needed),
and your other apps on the same VPS should still be reachable exactly as
before. Then open `https://app.<ip-with-dashes>.sslip.io` in a browser, sign
up, and confirm login/checkout/admin all work end to end.

To confirm the (now manual) tenant-domain path: set a tenant's
`custom_domain` (via `/admin` store settings) to another sslip.io hostname
pointing at the same IP (e.g. `myshop.<ip-with-dashes>.sslip.io`), then add
that same hostname to the `frontend` service's Domains list in Coolify —
it should get a cert and route to that tenant's storefront.

## 9. Backups

Coolify won't do this for you. Set up the existing backup script as a cron
job on the VPS itself (outside Coolify) — note the `.yaml` extension:

```
0 3 * * * cd /path/to/MultiVendor && ./deploy/backup_db.sh >> /var/log/multivendor-backup.log 2>&1
```

(`deploy/backup_db.sh` and `deploy/restore_db.sh` both reference
`docker-compose.prod.yaml` by default — if you're running the Coolify
Compose resource under a different project name/path, check
`docker compose -f docker-compose.coolify.yaml ps` resolves the same `mysql`
service name before relying on the script as-is.)

## 10. Moving to a real domain later

Buy a domain, point an A record at the VPS IP, then update the domain on
the `backend`/`frontend` services in Coolify's UI plus the matching
`APP_DOMAIN`/`API_DOMAIN` env vars, and redeploy.
