import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  // Self-contained production build (server.js + only the node_modules it
  // actually needs) -- Dockerfile copies just .next/standalone instead of
  // the full node_modules tree, which is most of why the prod image is
  // small. No effect on `next dev`.
  output: "standalone",
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
