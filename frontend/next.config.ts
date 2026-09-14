import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  // Self-contained production build (server.js + only the node_modules it
  // actually needs) -- Dockerfile copies just .next/standalone instead of
  // the full node_modules tree, which is most of why the prod image is
  // small. No effect on `next dev`.
  output: "standalone",
  // Tried experimental.trustHostHeader here to fix request.nextUrl.hostname
  // always reading as the server's bind address (0.0.0.0) instead of the
  // real incoming Host header on the standalone server -- doesn't work on
  // this Next.js version: its config Zod schema doesn't recognize the key
  // and silently strips it (see server/config.js's unrecognized_keys
  // handling for `experimental`), so it's always false at runtime regardless
  // of what's set here. Fixed instead in proxy.ts, which reads the Host
  // header directly off request.headers rather than through nextUrl.
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
