import { getCookie, deleteCookie } from 'cookies-next'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

export const apiClient = async (url: string, options: RequestInit = {}) => {
  const token = getCookie('token')
  const headers = new Headers(options.headers)

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  // Handle relative URLs to hit the live FastAPI backend
  const fullUrl = url.startsWith('/') ? `http://localhost:8000${url}` : url

  const response = await fetch(fullUrl, { ...options, headers })

  // Only treat a 401 as a session expiry if we actually sent a token — an
  // anonymous request (e.g. a failed login attempt) getting a 401 is not a
  // session to invalidate.
  if (response.status === 401 && token) {
    deleteCookie('token')
    deleteCookie('tenantSlug')
    if (typeof window !== 'undefined') {
      window.location.href = '/admin/login'
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, `HTTP Error ${response.status}`)
  }
  
  if (response.status === 204) return null
  return response.json()
}
