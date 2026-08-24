import { describe, it, expect } from 'vitest'
import { NextRequest } from 'next/server'
import crypto from 'crypto'
import { proxy } from '../proxy'

// Must match the secret vitest.setup.ts sets before this file is imported.
const TEST_SECRET = 'test-jwt-secret-for-vitest'

function makeJwt(payload: Record<string, unknown>, opts: { alg?: string; secret?: string } = {}) {
  const header = Buffer.from(JSON.stringify({ alg: opts.alg ?? 'HS256', typ: 'JWT' })).toString('base64url')
  const body = Buffer.from(JSON.stringify({
    exp: Math.floor(Date.now() / 1000) + 3600,
    typ: 'access',
    ...payload,
  })).toString('base64url')
  const signingInput = `${header}.${body}`
  const signature = crypto
    .createHmac('sha256', opts.secret ?? TEST_SECRET)
    .update(signingInput)
    .digest('base64url')
  return `${signingInput}.${signature}`
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

  it('rejects a token with a forged payload (valid shape, wrong signature) on /admin', () => {
    // Same structure as a real token, but the signature was never produced
    // by the backend's secret -- this is what decode-without-verify used to
    // let straight through.
    const forged = makeJwt({ role: 'user', store_role: 'tenant_admin' }, { secret: 'not-the-real-secret' })
    const res = proxy(makeRequest('/admin/dashboard', forged))
    expect(res.headers.get('location')).toContain('/admin/login')
  })

  it('rejects an alg-confusion token (alg: none) on /admin', () => {
    const forged = makeJwt({ role: 'user', store_role: 'tenant_admin' }, { alg: 'none' })
    const res = proxy(makeRequest('/admin/dashboard', forged))
    expect(res.headers.get('location')).toContain('/admin/login')
  })

  it('accepts a genuinely signed tenant_admin token on /admin', () => {
    const res = proxy(makeRequest('/admin/dashboard', makeJwt({ role: 'user', store_role: 'tenant_admin' })))
    expect(res.headers.get('location')).toBeNull()
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
