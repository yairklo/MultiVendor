'use client'

import React, { useEffect, useState } from 'react'
import { StorefrontThemeProvider } from '@/context/StorefrontThemeContext'
import { StorefrontHeader } from '@/components/storefront/StorefrontHeader'
import { StorefrontFooter } from '@/components/storefront/StorefrontFooter'

function displayName(slug: string): string {
  return slug
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

/**
 * Shared chrome for every page under /store/[tenant_slug] — header/nav, footer, and the
 * per-tenant theme they're styled with. Next's App Router never remounts this on client-side
 * navigation between child routes, which is what makes the cart (already global via
 * CartProvider in the root layout) and the nav/footer persist across Home/Shop/Product/About/
 * Contact without any per-page plumbing.
 */
export default function StorefrontLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: Promise<{ tenant_slug: string }> | { tenant_slug: string }
}) {
  const isPromise = params instanceof Promise
  const [tenantSlug, setTenantSlug] = useState<string | null>(isPromise ? null : (params as any).tenant_slug)

  useEffect(() => {
    if (isPromise) {
      ;(params as Promise<{ tenant_slug: string }>).then((p) => setTenantSlug(p.tenant_slug))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (!tenantSlug) return <div className="min-h-screen bg-gray-50" />

  const storeName = displayName(tenantSlug)

  return (
    <StorefrontThemeProvider tenantSlug={tenantSlug}>
      <div className="flex min-h-screen flex-col">
        <StorefrontHeader tenantSlug={tenantSlug} storeName={storeName} />
        <main className="flex-1">{children}</main>
        <StorefrontFooter tenantSlug={tenantSlug} storeName={storeName} />
      </div>
    </StorefrontThemeProvider>
  )
}
