import { describe, it, expect } from 'vitest'
import { NextRequest } from 'next/server'
import { proxy } from '../proxy'

function makeJwt(payload: Record<string, unknown>) {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url')
  const body = Buffer.from(JSON.stringify({
    exp: Math.floor(Date.now() / 1000) + 3600,
    typ: 'access',
    ...payload,
  })).toString('base64url')
  return `${header}.${body}.sig`
}

function makeRequest(pathname: string, token?: string) {
  const request = new NextRequest(new URL(`http://localhost:3000${pathname}`))
  if (token) request.cookies.set('token', token)
  return request
}

describe('proxy middleware', () => {
  it('redirects unauthenticated /admin requests to /admin/login', () => {
    const res = proxy(makeRequest('/admin/dashboard'))
    expect(res.headers.get('location')).toContain('/admin/login')
  })

  it('lets /admin/login through without a token', () => {
    const res = proxy(makeRequest('/admin/login'))
    expect(res.headers.get('location')).toBeNull()
  })

  it('lets tenant_admin /admin requests through', () => {
    const res = proxy(makeRequest('/admin/dashboard', makeJwt({ role: 'user', store_role: 'tenant_admin' })))
    expect(res.headers.get('location')).toBeNull()
  })

  it('lets super_admin /admin requests through', () => {
    const res = proxy(makeRequest('/admin/dashboard', makeJwt({ role: 'super_admin' })))
    expect(res.headers.get('location')).toBeNull()
  })

  it('rejects a customer token on /admin', () => {
    const res = proxy(makeRequest('/admin/dashboard', makeJwt({ role: 'user', store_role: 'customer' })))
    expect(res.headers.get('location')).toContain('/login')
  })

  it('rejects a raw non-JWT cookie on /admin and clears it', () => {
    const res = proxy(makeRequest('/admin/dashboard', 'valid-token'))
    expect(res.headers.get('location')).toContain('/admin/login')
    const cleared = res.headers.getSetCookie?.() ?? []
    expect(cleared.some((c) => c.startsWith('token='))).toBe(true)
  })

  it('redirects unauthenticated /super-admin requests', () => {
    const res = proxy(makeRequest('/super-admin'))
    expect(res.headers.get('location')).toContain('/admin/login')
  })

  it('rejects a tenant_admin on /super-admin', () => {
    const res = proxy(makeRequest('/super-admin', makeJwt({ role: 'user', store_role: 'tenant_admin' })))
    expect(res.headers.get('location')).toContain('/login')
  })

  it('redirects unauthenticated /crm requests', () => {
    const res = proxy(makeRequest('/crm'))
    expect(res.headers.get('location')).toContain('/admin/login')
  })

  it('does not touch unrelated routes', () => {
    const res = proxy(makeRequest('/store/some-tenant'))
    expect(res.headers.get('location')).toBeNull()
  })
})
