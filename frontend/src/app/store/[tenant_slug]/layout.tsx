import React from 'react'
import { cookies } from 'next/headers'
import { StorefrontThemeProvider } from '@/context/StorefrontThemeContext'
import { StorefrontHeader } from '@/components/storefront/StorefrontHeader'
import { StorefrontFooter } from '@/components/storefront/StorefrontFooter'
import { StorefrontBrandBackdrop } from '@/components/storefront/StorefrontBrandBackdrop'

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
export default async function StorefrontLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: Promise<{ tenant_slug: string }>
}) {
  const { tenant_slug: tenantSlug } = await params
  const storeName = displayName(tenantSlug)
  const cookieStore = await cookies()
  const isLoggedIn = !!cookieStore.get('token')?.value

  return (
    <StorefrontThemeProvider tenantSlug={tenantSlug}>
      <StorefrontBrandBackdrop>
        <div className="flex min-h-screen flex-col">
          <StorefrontHeader tenantSlug={tenantSlug} storeName={storeName} isLoggedIn={isLoggedIn} />
          <main className="flex-1">{children}</main>
          <StorefrontFooter tenantSlug={tenantSlug} storeName={storeName} />
        </div>
      </StorefrontBrandBackdrop>
    </StorefrontThemeProvider>
  )
}
