import { describe, it, expect } from 'vitest'
import { NextRequest } from 'next/server'
import { proxy } from '../proxy'

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

  it('lets authenticated /admin requests through', () => {
    const res = proxy(makeRequest('/admin/dashboard', 'valid-token'))
    expect(res.headers.get('location')).toBeNull()
  })

  it('redirects unauthenticated /super-admin requests', () => {
    const res = proxy(makeRequest('/super-admin'))
    expect(res.headers.get('location')).toContain('/admin/login')
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
