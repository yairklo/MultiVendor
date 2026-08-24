import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import crypto from 'crypto'

// Proxy runs in the Node.js runtime (this project's Next.js version defaults
// Proxy to Node, not Edge), so this must match the backend's
// app.core.config.settings.SECRET_KEY exactly (server/.env `SECRET_KEY`) for
// signatures to verify. Deliberately NOT NEXT_PUBLIC_* -- this file executes
// server-side only and the value must never ship to the client bundle.
const JWT_SECRET = process.env.JWT_SECRET_KEY

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

export function proxy(request: NextRequest) {
  const token = request.cookies.get('token')?.value
  const { pathname } = request.nextUrl

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
  matcher: [
    '/admin/:path*',
    '/super-admin/:path*',
    '/crm/:path*'
  ]
}
