import { getCookie, setCookie, deleteCookie } from 'cookies-next'

const TOKEN_COOKIE_NAME = 'token'
const TENANT_SLUG_COOKIE_NAME = 'tenantSlug'
const SEVEN_DAYS_SECONDS = 60 * 60 * 24 * 7

export interface SetAuthTokensParams {
  accessToken: string
  tenantSlug?: string | null
}

export function setAuthTokens({ accessToken, tenantSlug }: SetAuthTokensParams): void {
  const isSecure = typeof window !== 'undefined' ? window.location.protocol === 'https:' : false

  setCookie(TOKEN_COOKIE_NAME, accessToken, {
    maxAge: SEVEN_DAYS_SECONDS,
    path: '/',
    sameSite: 'lax',
    secure: isSecure,
  })

  if (tenantSlug) {
    setCookie(TENANT_SLUG_COOKIE_NAME, tenantSlug, {
      maxAge: SEVEN_DAYS_SECONDS,
      path: '/',
      sameSite: 'lax',
      secure: isSecure,
    })
  }
}

export function getAccessToken(): string | undefined {
  const token = getCookie(TOKEN_COOKIE_NAME)
  return typeof token === 'string' ? token : undefined
}

export function clearAuthTokens(): void {
  deleteCookie(TOKEN_COOKIE_NAME, { path: '/' })
  deleteCookie(TENANT_SLUG_COOKIE_NAME, { path: '/' })

  // Also trigger backend logout to clear the HttpOnly refresh token cookie
  try {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
    fetch(`${apiBase}/api/v1/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    }).catch(() => {
      // Best-effort cleanup, ignore network failures during logout
    })
  } catch {
    // Ignore in non-browser/SSR contexts
  }
}
