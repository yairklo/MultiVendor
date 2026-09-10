# Edge VPS (Caddy)

Caddy runs on its own dedicated VPS, separate from the app stack
(`docker-compose.prod.yml` at the repo root). This split exists because the
app VPS is a shared private box that already runs other, unrelated services
-- Caddy needs ports 80/443 exclusively (for ACME challenges, and so
`on_demand_tls` sees every incoming hostname before deciding whether to
issue it a certificate), which conflicts with whatever else is already
bound to those ports there. A single-VPS setup (Caddy + the app stack on
the same box) is simpler if you ever have a box dedicated to just this
project -- see the git history of `Caddyfile`/`docker-compose.prod.yml`
before this split for that version.

## Topology

```
internet
   |
   v
edge VPS (this directory)
   Caddy :80/:443 -- TLS termination, on-demand certs for custom domains
   |
   | plain HTTP, over a private network or a firewall-restricted link
   v
app VPS (repo root docker-compose.prod.yml)
   frontend :3000, backend :8000, mysql, redis
```

Both `APP_DOMAIN` and `API_DOMAIN` DNS records point at the **edge VPS's**
IP, not the app VPS's -- the edge VPS is the only thing that should ever be
reachable directly from the internet.

## Setup order

1. **App VPS first.** Deploy `docker-compose.prod.yml` there (see the repo
   root README's Deployment section). Note its IP address once it's up.
2. **Firewall the app VPS** so ports 3000 and 8000 are not reachable from
   the open internet -- only from the edge VPS. With `ufw`:
   ```bash
   sudo ufw allow from <edge-vps-ip> to any port 3000
   sudo ufw allow from <edge-vps-ip> to any port 8000
   sudo ufw deny 3000
   sudo ufw deny 8000
   ```
   Prefer your provider's private networking instead, if it has one
   (DigitalOcean, Hetzner, Vultr, and Linode all offer this, usually free,
   between VPS's on the same account/region): put `APP_UPSTREAM_HOST` on
   that private IP and the ports are never exposed publicly at all, firewall
   rule or not.
3. **Edge VPS.** Copy this `deploy/edge/` directory there, copy
   `.env.example` to `.env`, fill in `APP_UPSTREAM_HOST` with the app VPS's
   address from step 1, then:
   ```bash
   docker compose up -d --build
   ```

Skipping step 2 means the app is reachable over plain HTTP directly on
`<app-vps-ip>:3000`/`:8000`, bypassing TLS entirely and serving real traffic
(including login requests) in plaintext. Do it before step 3, not after.

## Why plain HTTP between the two VPS's is acceptable here (and when it isn't)

The edge-to-app hop carries real request/response traffic, same as any
reverse-proxy-to-origin hop. That's an acceptable amount of trust to put in
a link that's either a provider's private network (not internet-routable at
all) or a public link locked down by the firewall rule above (only the edge
VPS's IP can open a connection). If neither is true for your setup --
different providers, no private networking, and you can't firewall the app
VPS's ports -- put a WireGuard tunnel between the two boxes instead and
point `APP_UPSTREAM_HOST` at the tunnel's IP, rather than relying on
firewall rules alone over the open internet.
