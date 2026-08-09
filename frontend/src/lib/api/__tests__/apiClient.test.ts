import { describe, it, expect, vi, afterEach } from 'vitest'
import { apiClient, ApiError } from '../apiClient'

describe('API Client', () => {
  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('should automatically attach JWT Bearer token', async () => {
    localStorage.setItem('token', 'test-token')
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true })
    })

    await apiClient('/api/test')

    expect(global.fetch).toHaveBeenCalledWith('http://localhost:3000/api/test', expect.objectContaining({
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
})
