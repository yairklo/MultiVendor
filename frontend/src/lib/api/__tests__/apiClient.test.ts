import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { setCookie, deleteCookie } from 'cookies-next'
import { apiClient, ApiError } from '../apiClient'

describe('API Client', () => {
  afterEach(() => {
    deleteCookie('token')
    vi.restoreAllMocks()
  })

  it('should automatically attach JWT Bearer token', async () => {
    setCookie('token', 'test-token')
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true })
    })

    await apiClient('/api/test')

    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/test', expect.objectContaining({
      headers: expect.any(Headers)
    }))
    
    const callArgs = vi.mocked(global.fetch).mock.calls[0]
    const headers = callArgs[1]?.headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer test-token')
  })

  it('should handle error response interceptors', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ message: 'Unauthorized' })
    })

    await expect(apiClient('/api/test')).rejects.toThrow(ApiError)
    await expect(apiClient('/api/test')).rejects.toThrow('HTTP Error 401')
  })

  it('surfaces the backend FastAPI "detail" message instead of a generic status message', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Invalid coupon' })
    })

    await expect(apiClient('/api/test')).rejects.toThrow('Invalid coupon')
  })

  describe('session-expiry redirect', () => {
    let originalLocation: Location

    beforeEach(() => {
      originalLocation = window.location
    })

    afterEach(() => {
      Object.defineProperty(window, 'location', { value: originalLocation, writable: true })
    })

    const mockLocation = (pathname: string) => {
      Object.defineProperty(window, 'location', {
        value: { ...originalLocation, pathname, href: '' },
        writable: true,
      })
    }

    it('redirects to /admin/login when the session expires on an admin route', async () => {
      setCookie('token', 'test-token')
      mockLocation('/admin/products')
      global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({}) })

      await expect(apiClient('/api/test')).rejects.toThrow(ApiError)
      expect(window.location.href).toBe('/admin/login')
    })

    it('redirects to /login (not /admin/login) when the session expires on the storefront', async () => {
      setCookie('token', 'test-token')
      mockLocation('/store/test-tenant/products/test')
      global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({}) })

      await expect(apiClient('/api/test')).rejects.toThrow(ApiError)
      expect(window.location.href).toBe('/login')
    })
  })

  describe('refresh token interceptor & mutex queue', () => {
    it('seamlessly refreshes token on 401 and retries original request', async () => {
      setCookie('token', 'expired-token')

      let requestCount = 0
      global.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/api/v1/auth/refresh')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ access_token: 'refreshed-token', refresh_token: 'new-refresh-token' }),
          }
        }
        if (url.includes('/api/data')) {
          requestCount++
          if (requestCount === 1) {
            return { ok: false, status: 401, json: async () => ({ detail: 'Token expired' }) }
          }
          return { ok: true, status: 200, json: async () => ({ data: 'secret payload' }) }
        }
        return { ok: false, status: 404, json: async () => ({}) }
      })

      const res = await apiClient('/api/data')
      expect(res).toEqual({ data: 'secret payload' })
      expect(requestCount).toBe(2)

      // Ensure refresh was called with credentials: 'include'
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/refresh',
        expect.objectContaining({
          method: 'POST',
          credentials: 'include',
        })
      )
    })

    it('deduplicates concurrent 401s so only ONE refresh request is dispatched (mutex queue)', async () => {
      setCookie('token', 'expired-token')

      let refreshCalls = 0
      global.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/api/v1/auth/refresh')) {
          refreshCalls++
          // Small delay to simulate network latency
          await new Promise((resolve) => setTimeout(resolve, 20))
          return {
            ok: true,
            status: 200,
            json: async () => ({ access_token: 'new-token' }),
          }
        }
        if (url.includes('/api/data/')) {
          // Check authorization header
          const callArgs = vi.mocked(global.fetch).mock.calls
          const lastCall = callArgs[callArgs.length - 1]
          const headers = lastCall?.[1]?.headers as Headers | undefined
          const auth = headers?.get?.('Authorization')
          if (auth === 'Bearer new-token') {
            return { ok: true, status: 200, json: async () => ({ url, success: true }) }
          }
          return { ok: false, status: 401, json: async () => ({ detail: 'Unauthorized' }) }
        }
        return { ok: false, status: 404, json: async () => ({}) }
      })

      // Dispatch 3 requests concurrently
      const [res1, res2, res3] = await Promise.all([
        apiClient('/api/data/1'),
        apiClient('/api/data/2'),
        apiClient('/api/data/3'),
      ])

      expect(res1.success).toBe(true)
      expect(res2.success).toBe(true)
      expect(res3.success).toBe(true)
      // Exactly 1 refresh call should have taken place!
      expect(refreshCalls).toBe(1)
    })

    it('does not attempt refresh or tear down session when 401 occurs on /api/v1/auth/login', async () => {
      setCookie('token', 'existing-token')
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Invalid credentials' }),
      })

      await expect(
        apiClient('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({}) })
      ).rejects.toThrow('Invalid credentials')

      // Should not have called /refresh
      const fetchCalls = vi.mocked(global.fetch).mock.calls
      const refreshCalls = fetchCalls.filter(([callUrl]) => String(callUrl).includes('/auth/refresh'))
      expect(refreshCalls.length).toBe(0)

      // Should not have called /logout or deleted the existing token
      const logoutCalls = fetchCalls.filter(([callUrl]) => String(callUrl).includes('/auth/logout'))
      expect(logoutCalls.length).toBe(0)
    })

    it('prevents infinite loops by immediately rejecting when a retried request receives 401', async () => {
      setCookie('token', 'valid-token')

      let refreshCalls = 0
      global.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/api/v1/auth/refresh')) {
          refreshCalls++
          return {
            ok: true,
            status: 200,
            json: async () => ({ access_token: 'new-token' }),
          }
        }
        // Always 401 even after retry
        return { ok: false, status: 401, json: async () => ({ detail: 'Still unauthorized' }) }
      })

      // When called with _retry: true, should never call refresh
      await expect(apiClient('/api/test', { _retry: true })).rejects.toThrow(ApiError)
      expect(refreshCalls).toBe(0)
    })
  })
})
