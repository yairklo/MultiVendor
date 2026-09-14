import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  // Self-contained production build (server.js + only the node_modules it
  // actually needs) -- Dockerfile copies just .next/standalone instead of
  // the full node_modules tree, which is most of why the prod image is
  // small. No effect on `next dev`.
  output: "standalone",
  experimental: {
    // Without this, the standalone server builds Proxy's `request.nextUrl`
    // (and thus `request.nextUrl.hostname`) from its own bind address
    // (HOSTNAME=0.0.0.0, see Dockerfile) instead of the incoming `Host`
    // header -- see resolve-routes.js's `initUrl` construction. Every
    // request's hostname was literally "0.0.0.0" regardless of what Caddy/
    // Traefik forwarded, so proxy.ts's isPlatformHost(hostname) always
    // returned false and every non-whitelisted path (including
    // /store/[tenant_slug] and even /) fell through to the "unresolved
    // custom domain" 404. Safe to trust here because Caddy/Coolify's
    // Traefik are the only things that can reach this container (no public
    // ports exposed directly -- see docker-compose.prod.yaml /
    // docker-compose.coolify.yaml), so the Host header they forward is
    // trustworthy.
    trustHostHeader: true,
  } as NextConfig["experimental"],
  async headers() {
    // No Content-Security-Policy here: with product/store images and logos
    // coming from arbitrary seller-supplied URLs (see app/services/storage
    // on the backend), a CSP tight enough to matter would need per-tenant
    // image-source allowlisting, not a single static policy.
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },
};

export default nextConfig;
