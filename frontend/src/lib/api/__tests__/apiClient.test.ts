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
})
