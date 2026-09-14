import React from 'react'
import { cookies } from 'next/headers'
import { StorefrontThemeProvider } from '@/context/StorefrontThemeContext'
import { StorefrontHeader } from '@/components/storefront/StorefrontHeader'
import { StorefrontFooter } from '@/components/storefront/StorefrontFooter'
import { StorefrontBrandBackdrop } from '@/components/storefront/StorefrontBrandBackdrop'
import { isUsableTenantSlug } from '@/lib/tenantSlug'

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
  if (!isUsableTenantSlug(tenantSlug)) {
    // Was `notFound()` (throws, caught by the nearest not-found boundary) --
    // on this deploy that throw-based mechanism surfaces as a bare 404 for
    // *every* request under this layout, valid slugs included, not just
    // this rejection case. A framework-level issue still being tracked, not
    // something introduced here. Rendering a plain in-place message instead
    // avoids the broken throw path entirely; this branch only ever runs for
    // the JS-stringified-undefined sentinels this guard exists to catch
    // (see isUsableTenantSlug's docstring), not real traffic.
    return (
      <div className="flex min-h-screen items-center justify-center p-8 text-center">
        <p>Store not found.</p>
      </div>
    )
  }
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
