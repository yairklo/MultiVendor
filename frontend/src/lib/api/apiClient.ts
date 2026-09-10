import { getAccessToken, setAuthTokens, clearAuthTokens } from '@/lib/auth/tokenStorage'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

export interface ApiClientOptions extends RequestInit {
  _retry?: boolean
}

let refreshPromise: Promise<string | null> | null = null

async function requestTokenRefresh(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
        // Relies 100% on the HttpOnly refresh_token cookie sent automatically via credentials: 'include'
        const res = await fetch(`${apiBase}/api/v1/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
        })

        if (!res.ok) {
          return null
        }

        const data = await res.json()
        if (data && data.access_token) {
          // Frontend in the browser completely ignores data.refresh_token and only stores the access token
          setAuthTokens({
            accessToken: data.access_token,
          })
          return data.access_token as string
        }
        return null
      } catch {
        return null
      } finally {
        refreshPromise = null
      }
    })()
  }
  return refreshPromise
}

export const apiClient = async (url: string, options: ApiClientOptions = {}): Promise<any> => {
  const token = getAccessToken()
  const headers = new Headers(options.headers)

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  
  // A FormData body (file uploads) must NOT get an explicit Content-Type --
  // the browser sets its own multipart boundary, which we can't replicate.
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  // Handle relative URLs to hit the live FastAPI backend
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
  const fullUrl = url.startsWith('/') ? `${apiBase}${url}` : url

  // Needed for HttpOnly cookies (refresh_token, cart_token) to be sent/received
  // on this cross-origin (but same-site, see frontend/.env.local) call --
  // without it the browser drops Set-Cookie from the response entirely.
  const response = await fetch(fullUrl, { ...options, headers, credentials: 'include' })

  // Identify auth endpoints that should NOT trigger a refresh loop on 401
  const isAuthEndpoint = url.includes('/api/v1/auth/login') || url.includes('/api/v1/auth/refresh')

  if (response.status === 401 && token && !isAuthEndpoint && !options._retry) {
    const newAccessToken = await requestTokenRefresh()
    if (newAccessToken) {
      const retryHeaders = new Headers(options.headers)
      retryHeaders.set('Authorization', `Bearer ${newAccessToken}`)
      return apiClient(url, { ...options, headers: retryHeaders, _retry: true })
    }

    // Refresh failed or returned null — perform full cleanup and redirect
    clearAuthTokens()
    if (typeof window !== 'undefined') {
      const isAdminRoute = /^\/(admin|super-admin)(\/|$)/.test(window.location.pathname)
      window.location.href = isAdminRoute ? '/admin/login' : '/login'
    }
  } else if (response.status === 401 && token && (isAuthEndpoint || options._retry)) {
    // Only clear tokens if an active session expired on retry or on an authenticated route
    clearAuthTokens()
    if (typeof window !== 'undefined' && options._retry) {
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
