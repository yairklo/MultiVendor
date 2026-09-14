import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  // Self-contained production build (server.js + only the node_modules it
  // actually needs) -- Dockerfile copies just .next/standalone instead of
  // the full node_modules tree, which is most of why the prod image is
  // small. No effect on `next dev`.
  output: "standalone",
  // The platform has no single-tenant "home" -- the marketplace listing is
  // the natural landing page for a visitor who hasn't picked a store yet
  // (see the removed app/page.tsx). Done here instead of an in-component
  // redirect() call: on this deploy, a Server Component's redirect()/
  // notFound() throw was surfacing as a bare 404 instead of performing the
  // redirect/rendering the not-found UI -- a framework-level issue still
  // being tracked, not something this app's code caused. A config-level
  // redirect happens at the routing layer, before any component renders, so
  // it isn't subject to whatever's breaking that throw-based mechanism.
  async redirects() {
    return [
      { source: "/", destination: "/marketplace", permanent: false },
    ];
  },
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
