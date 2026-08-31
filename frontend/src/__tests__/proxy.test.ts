import { describe, it, expect } from 'vitest'
import { NextRequest } from 'next/server'
import crypto from 'crypto'
import { http, HttpResponse } from 'msw'
import { server } from '../mocks/server'
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

function makeRequest(pathname: string, token?: string, host = 'localhost:3000') {
  const request = new NextRequest(new URL(`http://${host}${pathname}`))
  if (token) request.cookies.set('token', token)
  return request
}

describe('proxy middleware', () => {
  it('redirects unauthenticated /admin requests to /admin/login', async () => {
    const res = await proxy(makeRequest('/admin/dashboard'))
    expect(res.headers.get('location')).toContain('/admin/login')
  })

  it('lets /admin/login through without a token', async () => {
    const res = await proxy(makeRequest('/admin/login'))
    expect(res.headers.get('location')).toBeNull()
  })

  it('lets tenant_admin /admin requests through', async () => {
    const res = await proxy(makeRequest('/admin/dashboard', makeJwt({ role: 'user', store_role: 'tenant_admin' })))
    expect(res.headers.get('location')).toBeNull()
  })

  it('lets super_admin /admin requests through', async () => {
    const res = await proxy(makeRequest('/admin/dashboard', makeJwt({ role: 'super_admin' })))
    expect(res.headers.get('location')).toBeNull()
  })

  it('rejects a customer token on /admin', async () => {
    const res = await proxy(makeRequest('/admin/dashboard', makeJwt({ role: 'user', store_role: 'customer' })))
    expect(res.headers.get('location')).toContain('/login')
  })

  it('rejects a raw non-JWT cookie on /admin and clears it', async () => {
    const res = await proxy(makeRequest('/admin/dashboard', 'valid-token'))
    expect(res.headers.get('location')).toContain('/admin/login')
    const cleared = res.headers.getSetCookie?.() ?? []
    expect(cleared.some((c) => c.startsWith('token='))).toBe(true)
  })

  it('rejects a token with a forged payload (valid shape, wrong signature) on /admin', async () => {
    // Same structure as a real token, but the signature was never produced
    // by the backend's secret -- this is what decode-without-verify used to
    // let straight through.
    const forged = makeJwt({ role: 'user', store_role: 'tenant_admin' }, { secret: 'not-the-real-secret' })
    const res = await proxy(makeRequest('/admin/dashboard', forged))
    expect(res.headers.get('location')).toContain('/admin/login')
  })

  it('rejects an alg-confusion token (alg: none) on /admin', async () => {
    const forged = makeJwt({ role: 'user', store_role: 'tenant_admin' }, { alg: 'none' })
    const res = await proxy(makeRequest('/admin/dashboard', forged))
    expect(res.headers.get('location')).toContain('/admin/login')
  })

  it('accepts a genuinely signed tenant_admin token on /admin', async () => {
    const res = await proxy(makeRequest('/admin/dashboard', makeJwt({ role: 'user', store_role: 'tenant_admin' })))
    expect(res.headers.get('location')).toBeNull()
  })

  it('redirects unauthenticated /super-admin requests', async () => {
    const res = await proxy(makeRequest('/super-admin'))
    expect(res.headers.get('location')).toContain('/admin/login')
  })

  it('rejects a tenant_admin on /super-admin', async () => {
    const res = await proxy(makeRequest('/super-admin', makeJwt({ role: 'user', store_role: 'tenant_admin' })))
    expect(res.headers.get('location')).toContain('/login')
  })

  it('redirects unauthenticated /crm requests', async () => {
    const res = await proxy(makeRequest('/crm'))
    expect(res.headers.get('location')).toContain('/admin/login')
  })

  it('does not touch unrelated routes on the platform domain', async () => {
    const res = await proxy(makeRequest('/store/some-tenant'))
    expect(res.headers.get('location')).toBeNull()
  })
})

describe('proxy middleware -- custom domains', () => {
  it('rewrites a claimed custom domain to its /store/{slug} route', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/store/resolve-domain', ({ request }) => {
        const domain = new URL(request.url).searchParams.get('domain')
        if (domain === 'shop.sellerbrand.example') {
          return HttpResponse.json({ tenant_slug: 'seller-brand' })
        }
        return new HttpResponse(null, { status: 404 })
      })
    )

    const res = await proxy(makeRequest('/products/widget', undefined, 'shop.sellerbrand.example'))
    expect(res.headers.get('x-middleware-rewrite')).toContain('/store/seller-brand/products/widget')
  })

  it('rewrites a claimed custom domain root to /store/{slug} with no trailing path', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/store/resolve-domain', () =>
        HttpResponse.json({ tenant_slug: 'seller-brand' })
      )
    )

    const res = await proxy(makeRequest('/', undefined, 'shop.sellerbrand.example'))
    expect(res.headers.get('x-middleware-rewrite')).toContain('/store/seller-brand')
  })

  it('404s an unclaimed custom domain instead of rewriting it', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/store/resolve-domain', () => new HttpResponse(null, { status: 404 }))
    )

    const res = await proxy(makeRequest('/', undefined, 'nobody-owns-this.example'))
    expect(res.status).toBe(404)
  })

  it('leaves platform-only paths (checkout, login, admin, ...) unrewritten even on a custom domain', async () => {
    const res = await proxy(makeRequest('/checkout', undefined, 'shop.sellerbrand.example'))
    expect(res.headers.get('x-middleware-rewrite')).toBeNull()
    expect(res.status).not.toBe(404)
  })

  it('treats the platform domain itself as platform, not a tenant custom domain', async () => {
    const res = await proxy(makeRequest('/some-page', undefined, 'app.example.com'))
    expect(res.headers.get('x-middleware-rewrite')).toBeNull()
    expect(res.status).not.toBe(404)
  })
})
