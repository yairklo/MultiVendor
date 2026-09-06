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
TLS for domains explicitly registered per application, via its API or UI.

To keep this close to zero-touch anyway, `server/app/services/coolify_service.py`
calls that API automatically whenever a tenant sets/changes their
`custom_domain` (wired into `update_tenant_service` in
`server/app/services/tenant_service.py`) — see step 5 below to turn it on.
**Read this before relying on it**: Coolify's docker-compose domain-update
API has real, open bugs in some versions
([coollabsio/coolify#4999](https://github.com/coollabsio/coolify/issues/4999),
[#4326](https://github.com/coollabsio/coolify/issues/4326)). The
integration is deliberately best-effort — a failure is logged and swallowed,
never breaks the tenant admin's settings save, and it refuses to write
anything if the domains it reads back from Coolify don't already include
the platform's own `APP_DOMAIN` (a sign its parsing doesn't match your
Coolify version's actual response shape, safer to abstain than guess). The
manual fallback (add the domain by hand in Coolify's UI, per step 4) always
still works regardless. **Verify the API call manually against your own
Coolify instance (see step 5) before assuming the automation is actually
working** — don't just trust that it's silently succeeding.

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

## 5. (Optional) Enable automatic tenant-domain registration

Skip this step to keep manual domain adds (step 4's approach, done again by
hand each time a tenant sets a custom domain). To automate it instead:

1. Coolify → your avatar/team → **Keys & Tokens → API tokens** → create a
   token. Give it only the permissions it needs to read/update
   applications — not a root/admin-everything token, since this value ends
   up in the backend's environment.
2. Find the `frontend` service's application UUID: open it in Coolify and
   copy the UUID from the page URL (`.../application/<uuid>`).
3. Before trusting this in production, verify it actually works against
   *your* Coolify version:
   ```bash
   curl -s -H "Authorization: Bearer <token>" \
     https://<your-coolify-host>/api/v1/applications/<uuid> | head -c 2000
   ```
   Confirm the response actually has a `docker_compose_domains` field shaped
   like `[{"domain": "...", "container": "frontend"}]` — if it looks
   different, the automation's parsing (in `coolify_service.py`) won't
   recognize your existing domains and will safely no-op (see the tradeoff
   note above) rather than risk corrupting them.
4. Set `COOLIFY_API_URL` (e.g. `https://<your-coolify-host>/api/v1`),
   `COOLIFY_API_TOKEN`, and `COOLIFY_FRONTEND_APP_UUID` in step 6's env vars.

## 6. Set environment variables (in Coolify's resource → Environment Variables)

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
| `COOLIFY_API_URL`, `COOLIFY_API_TOKEN`, `COOLIFY_FRONTEND_APP_UUID` | only if you did step 5 — otherwise leave all three blank |

`ACME_EMAIL` is not needed here — that was only for Caddy. Coolify already
has its own ACME email configured server-wide for its shared proxy.

Everything left blank above degrades to a safe disabled/mock mode — see
`.env.example` at the repo root for the full reference and what each one
unlocks.

## 7. Deploy

Click Deploy in Coolify. It builds `server/Dockerfile` and
`frontend/Dockerfile`, brings up `mysql`, `redis`, `backend`, `frontend`,
and the shared proxy requests real Let's Encrypt certs for both domains on
first request (may take ~10-30s the very first time each hostname is hit).

## 8. Run migrations + seed data (one-time, after first deploy)

Exec into the `backend` container from Coolify's UI (or SSH + `docker exec`)
and run:

```bash
alembic upgrade head
python seed_db.py   # optional — creates a demo tenant + sample data
```

## 9. Verify

```bash
curl -I https://api.<ip-with-dashes>.sslip.io/health
curl -I https://app.<ip-with-dashes>.sslip.io
```

Both should return `200`/`30x` with a valid TLS handshake (no `-k` needed),
and your other apps on the same VPS should still be reachable exactly as
before. Then open `https://app.<ip-with-dashes>.sslip.io` in a browser, sign
up, and confirm login/checkout/admin all work end to end.

To confirm the tenant-domain path: set a tenant's `custom_domain` (via
`/admin` store settings) to another sslip.io hostname pointing at the same
IP (e.g. `myshop.<ip-with-dashes>.sslip.io`).

- **If you did step 5**, check the backend logs for a `coolify_service`
  error first (it logs and swallows failures rather than raising) — if
  clean, check the `frontend` app's Domains list in Coolify actually grew
  to include it. Don't assume success just because the request returned
  200; confirm the domain really shows up there.
- **Either way** (automated or not), as a fallback add the hostname to the
  `frontend` service's Domains list in Coolify by hand if it isn't there
  yet — it should get a cert and route to that tenant's storefront.

## 10. Backups

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

## 11. Moving to a real domain later

Buy a domain, point an A record at the VPS IP, then update the domain on
the `backend`/`frontend` services in Coolify's UI plus the matching
`APP_DOMAIN`/`API_DOMAIN` env vars, and redeploy.
