import 'server-only'
import { cache } from 'react'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { ApiError } from './apiClient'

export { ApiError }

export async function getServerTenantSlug() {
  const cookieStore = await cookies()
  return cookieStore.get('tenantSlug')?.value || 'test-tenant'
}

export const serverApiClient = async (url: string, options: RequestInit = {}) => {
  const cookieStore = await cookies()
  const token = cookieStore.get('token')?.value
  const headers = new Headers(options.headers)

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
  const fullUrl = url.startsWith('/') ? `${apiBase}${url}` : url

  const response = await fetch(fullUrl, { ...options, headers })

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

// The admin/(cms) and super-admin routes are only reachable with a token
// (proxy.ts middleware), but that token can still expire mid-session. The old
// client-side apiClient caught a 401 globally and bounced to /admin/login —
// this is that same behavior for the server-fetched admin pages, since a
// Server Component can't do a window.location redirect.
export async function adminApiClient(url: string, options: RequestInit = {}) {
  try {
    return await serverApiClient(url, options)
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      redirect('/admin/login')
    }
    throw e
  }
}

// Cached per-request so a page body and its generateMetadata (which both need
// the same tenant home layout) share one fetch instead of hitting the backend twice.
export const getTenantHomeLayout = cache(async (tenantSlug: string) => {
  try {
    return await serverApiClient(`/api/v1/store/${tenantSlug}/pages/home`)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null
    throw e
  }
})

export const getTenantPage = cache(async (tenantSlug: string, pageKey: string) => {
  return serverApiClient(`/api/v1/store/${tenantSlug}/pages/${pageKey}`)
})

export const getProduct = cache(async (tenantSlug: string, slug: string) => {
  return serverApiClient(`/api/v1/store/${tenantSlug}/products/${slug}`)
})

export const getProducts = cache(
  async (tenantSlug: string, page = 1, pageSize = 20, searchParams?: Record<string, string>) => {
    const qs = new URLSearchParams({ page: String(page), page_size: String(pageSize), ...searchParams })
    const data = await serverApiClient(`/api/v1/store/${tenantSlug}/products?${qs.toString()}`)
    return { data: data.data || [], meta: data.meta }
  }
)

export const getCategories = cache(async (tenantSlug: string) => {
  const data = await serverApiClient(`/api/v1/store/${tenantSlug}/categories`)
  return data.data || data
})

export const getProductReviews = cache(async (tenantSlug: string, slug: string) => {
  try {
    return await serverApiClient(`/api/v1/store/${tenantSlug}/products/${slug}/reviews`)
  } catch {
    return []
  }
})
