import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.')
    if (parts.length < 2) return null
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
    return JSON.parse(atob(padded))
  } catch {
    return null
  }
}

function isUsableAccessToken(token: string | undefined): Record<string, unknown> | null {
  if (!token) return null
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
