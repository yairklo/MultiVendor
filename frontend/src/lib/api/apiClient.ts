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
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
  const fullUrl = url.startsWith('/') ? `${apiBase}${url}` : url

  const response = await fetch(fullUrl, { ...options, headers })

  // Only treat a 401 as a session expiry if we actually sent a token — an
  // anonymous request (e.g. a failed login attempt) getting a 401 is not a
  // session to invalidate.
  if (response.status === 401 && token) {
    deleteCookie('token')
    deleteCookie('tenantSlug')
    if (typeof window !== 'undefined') {
      // Redirect to the login page that actually matches where the session
      // expired — a shopper's expired session on the storefront has no
      // business landing on the admin login screen, and vice versa.
      const isAdminRoute = /^\/(admin|super-admin)(\/|$)/.test(window.location.pathname)
      window.location.href = isAdminRoute ? '/admin/login' : '/login'
    }
  }

  if (!response.ok) {
    // FastAPI error responses are {"detail": "..."} — surface that instead
    // of a generic status message wherever the backend provides one.
    let detail: string | undefined
    try {
      const body = await response.json()
      detail = typeof body?.detail === 'string' ? body.detail : undefined
    } catch {
      // Response body wasn't JSON (or already consumed) — fall back below.
    }
    throw new ApiError(response.status, detail || `HTTP Error ${response.status}`)
  }
  
  if (response.status === 204) return null
  return response.json()
}
