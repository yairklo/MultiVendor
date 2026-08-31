import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import crypto from 'crypto'

// Proxy runs in the Node.js runtime (this project's Next.js version defaults
// Proxy to Node, not Edge), so this must match the backend's
// app.core.config.settings.SECRET_KEY exactly (server/.env `SECRET_KEY`) for
// signatures to verify. Deliberately NOT NEXT_PUBLIC_* -- this file executes
// server-side only and the value must never ship to the client bundle.
const JWT_SECRET = process.env.JWT_SECRET_KEY

// The platform's own frontend domain (see docker-compose.prod.yml / Caddyfile).
// Unset in local dev, which means isPlatformHost() below always returns true --
// no request is ever treated as a tenant custom domain locally.
const APP_DOMAIN = process.env.APP_DOMAIN

// Reaches the backend directly over the docker network in prod
// (docker-compose.prod.yml sets this to http://backend:8000) rather than
// bouncing back out through Caddy/the public API domain. Falls back to the
// same base URL the browser bundle uses, which is already correct for local
// dev (both point at localhost).
const INTERNAL_API_BASE_URL = process.env.INTERNAL_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

// Routes that exist at the platform level and are never part of a specific
// store's /store/{slug} tree -- these pass through unrewritten even when
// reached via a tenant's custom domain. A tenant admin managing their store
// is expected to do it from the platform's own domain, not their public
// storefront domain (the same split Shopify/most SaaS platforms use), so
// /admin and /super-admin are deliberately NOT reachable via a custom domain.
const PLATFORM_ONLY_PATHS = [
  '/checkout', '/login', '/signup', '/forgot-password', '/reset-password',
  '/account', '/marketplace', '/admin', '/super-admin', '/crm',
]

// This proxy runs as a long-lived Node.js process (not the stateless Edge
// runtime), so a module-level cache actually persists across requests and
// saves a resolve-domain round trip to the backend on every single page
// view of a custom domain.
const DOMAIN_CACHE_TTL_MS = 5 * 60 * 1000
const domainCache = new Map<string, { slug: string | null; expiresAt: number }>()

async function resolveTenantSlugForHost(hostname: string): Promise<string | null> {
  const cached = domainCache.get(hostname)
  if (cached && cached.expiresAt > Date.now()) return cached.slug

  let slug: string | null = null
  try {
    const res = await fetch(
      `${INTERNAL_API_BASE_URL}/api/v1/store/resolve-domain?domain=${encodeURIComponent(hostname)}`
    )
    if (res.ok) {
      const data = await res.json()
      if (typeof data.tenant_slug === 'string') slug = data.tenant_slug
    }
  } catch {
    // Backend unreachable -- resolve to "unclaimed" rather than throwing, so
    // a transient backend outage 404s just this request instead of taking
    // down the proxy for every request on every host.
  }

  domainCache.set(hostname, { slug, expiresAt: Date.now() + DOMAIN_CACHE_TTL_MS })
  return slug
}

function isPlatformHost(hostname: string): boolean {
  if (!APP_DOMAIN) return true
  return hostname === APP_DOMAIN || hostname === 'localhost' || hostname === '127.0.0.1'
}

function base64UrlDecode(input: string): Buffer | null {
  try {
    return Buffer.from(input, 'base64url')
  } catch {
    return null
  }
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.')
    if (parts.length < 2) return null
    const raw = base64UrlDecode(parts[1])
    if (!raw) return null
    return JSON.parse(raw.toString('utf-8'))
  } catch {
    return null
  }
}

// Decoding a JWT payload only tells you what the cookie *claims*; it proves
// nothing on its own since any client can hand-craft a base64url JSON blob
// with role: "super_admin" in it. This step is what makes the claims
// trustworthy: it recomputes the HMAC over header+payload and compares it
// (constant-time) against the signature the token carries.
function hasValidSignature(token: string): boolean {
  if (!JWT_SECRET) {
    // Fail closed: with no configured secret nothing can be verified, so no
    // token should be trusted enough to reach /admin, /super-admin, or /crm.
    return false
  }

  const parts = token.split('.')
  if (parts.length !== 3) return false
  const [headerB64, payloadB64, signatureB64] = parts

  const headerRaw = base64UrlDecode(headerB64)
  if (!headerRaw) return false
  let header: Record<string, unknown>
  try {
    header = JSON.parse(headerRaw.toString('utf-8'))
  } catch {
    return false
  }
  // Reject alg confusion (e.g. "none" or a downgrade to a different scheme)
  // -- the backend (app/core/security.py) only ever signs with HS256.
  if (header.alg !== 'HS256') return false

  const signature = base64UrlDecode(signatureB64)
  if (!signature) return false

  const expected = crypto.createHmac('sha256', JWT_SECRET).update(`${headerB64}.${payloadB64}`).digest()
  if (signature.length !== expected.length) return false
  return crypto.timingSafeEqual(signature, expected)
}

function isUsableAccessToken(token: string | undefined): Record<string, unknown> | null {
  if (!token) return null
  if (!hasValidSignature(token)) return null
  const payload = decodeJwtPayload(token)
  if (!payload) return null
  if (payload.typ === 'refresh') return null
  if (typeof payload.exp === 'number' && payload.exp * 1000 < Date.now()) return null
  return payload
}

function canAccessAdmin(payload: Record<string, unknown>): boolean {
  return (
    payload.role === 'super_admin' ||
    payload.store_role === 'tenant_admin' ||
    payload.is_super_admin === true
  )
}

export async function proxy(request: NextRequest) {
  const { pathname, hostname } = request.nextUrl

  if (!isPlatformHost(hostname)) {
    const isPlatformOnlyPath = PLATFORM_ONLY_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`))
    if (isPlatformOnlyPath) {
      return NextResponse.next()
    }

    const slug = await resolveTenantSlugForHost(hostname)
    if (!slug) {
      return new NextResponse('Not Found', { status: 404 })
    }

    // The address bar keeps showing the seller's own domain; Next.js
    // internally serves the matching /store/{slug} route underneath it.
    const url = request.nextUrl.clone()
    url.pathname = `/store/${slug}${pathname === '/' ? '' : pathname}`
    return NextResponse.rewrite(url)
  }

  const token = request.cookies.get('token')?.value

  const isAdmin = pathname.startsWith('/admin') && !pathname.startsWith('/admin/login')
  const isSuperAdmin = pathname.startsWith('/super-admin')
  const isCrm = pathname.startsWith('/crm')

  if (!isAdmin && !isSuperAdmin && !isCrm) {
    return NextResponse.next()
  }

  const payload = isUsableAccessToken(token)
  const loginUrl = new URL('/admin/login', request.url)

  if (!payload) {
    const res = NextResponse.redirect(loginUrl)
    if (token) {
      res.cookies.delete('token')
      res.cookies.delete('tenantSlug')
    }
    return res
  }

  if (isSuperAdmin && payload.role !== 'super_admin' && payload.is_super_admin !== true) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  if ((isAdmin || isCrm) && !canAccessAdmin(payload)) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  // Broadened from just /admin, /super-admin, /crm: the custom-domain
  // rewrite above has to see every request (a seller's storefront root, a
  // product page, ...), not just the admin surfaces. Excludes static assets
  // -- those are served identically regardless of which domain asked for them.
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
