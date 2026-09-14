FROM node:24-alpine AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:24-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .
# NEXT_PUBLIC_* values are baked into the client bundle at build time, not
# read at runtime -- must be passed as build args, not just env on the
# running container. See docker-compose.prod.yaml.
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
# package.json's build script passes --turbopack -- confirmed necessary, not
# just faster, on this Next.js version: a plain `next build` (webpack, the
# default) produces a standalone server that 404s on every dynamic route
# added/changed after the very first build, even though routes-manifest.json,
# app-paths-manifest.json, and the compiled route files are all correct --
# reproduced locally multiple times (fresh checkout, no Docker cache
# involved). Switching to --turbopack (also `next dev`'s default already)
# makes the exact same routes serve correctly. If a future Next.js patch
# fixes the webpack path, this can revert to a plain `next build`.
RUN npm run build

# --- Runtime image: only what `output: "standalone"` says the server needs
# (server.js + a pruned node_modules), not the full builder stage.
FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
