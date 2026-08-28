'use client'

import { useSyncExternalStore } from 'react'
import { getCookie } from 'cookies-next'

/**
 * Reads the 'tenantSlug' cookie safely across SSR/hydration.
 *
 * getCookie() only sees the real cookie client-side -- there's no `document` during the
 * server render pass every 'use client' component still gets for its first paint -- so
 * reading it directly during render would make the server-rendered HTML and the client's
 * first hydration pass disagree. Deferring the real read to an effect keeps the first
 * render identical on both sides (empty string); the effect then swaps in the cookie
 * value after mount.
 *
 * There is no default store slug. Consumers that fetch tenant-scoped data must skip
 * while this hook still returns an empty string.
 */
export const PLACEHOLDER_TENANT_SLUG = ''

// Cookies don't dispatch a change event to subscribe to -- useSyncExternalStore
// still gets the SSR/hydration behavior right without one: it renders
// getServerSnapshot() (empty string) on both the server and the first client
// render to match, then re-reads getSnapshot() right after mount and
// re-renders if the real cookie value differs.
function subscribe(): () => void {
  return () => {}
}

function getSnapshot(): string {
  const cookieSlug = getCookie('tenantSlug')
  return cookieSlug ? String(cookieSlug) : ''
}

function getServerSnapshot(): string {
  return ''
}

export function useTenantSlug(): string {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}
