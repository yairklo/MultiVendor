import { cookies } from 'next/headers'
import { Metadata } from 'next'
import { getTenantHomeLayout } from '@/lib/api/serverApiClient'
import { CatalogListing } from '@/components/storefront/CatalogListing'
import { StorefrontThemeProvider } from '@/context/StorefrontThemeContext'
import { StorefrontHeader } from '@/components/storefront/StorefrontHeader'
import { StorefrontFooter } from '@/components/storefront/StorefrontFooter'
import { StorefrontBrandBackdrop } from '@/components/storefront/StorefrontBrandBackdrop'
import { isUsableTenantSlug } from '@/lib/tenantSlug'

// Query-param twin of /store/[tenant_slug] (?slug=store1 instead of a
// dynamic path segment) -- a stopgap while that route 404s on this deploy
// for reasons still being tracked (confirmed not our component code: the
// request never reaches this layout/page pair at all, despite a correct
// routes-manifest entry and the compiled output being present). Static
// routes with no dynamic segment (this one, /marketplace, /login,
// /admin/login) are unaffected, so reusing the exact same components here
// sidesteps whatever's broken rather than fixing it. Remove once the real
// cause of the [tenant_slug] 404 is found and /store/[tenant_slug] is
// confirmed working again -- this route is not meant to be permanent.

function displayName(slug: string): string {
  return slug
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

type SearchParams = { slug?: string }

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<SearchParams>
}): Promise<Metadata> {
  const { slug } = await searchParams
  const decodedSlug = slug ? decodeURIComponent(slug) : ''
  const capitalizedSlug = decodedSlug.charAt(0).toUpperCase() + decodedSlug.slice(1)

  return {
    title: capitalizedSlug || 'Store',
    description: capitalizedSlug ? `Welcome to ${capitalizedSlug} on MultiVendor` : undefined,
  }
}

export default async function StorefrontQueryPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>
}) {
  const { slug } = await searchParams
  const tenantSlug = slug ?? ''

  if (!isUsableTenantSlug(tenantSlug)) {
    return (
      <div className="flex min-h-screen items-center justify-center p-8 text-center">
        <p>Store not found.</p>
      </div>
    )
  }

  const storeName = displayName(tenantSlug)
  const cookieStore = await cookies()
  const isLoggedIn = !!cookieStore.get('token')?.value

  // Same data source as /store/[tenant_slug]/page.tsx -- CatalogListing
  // falls back to the classic catalog listing when there is none yet
  // (aiPage stays null), so untouched stores are unaffected.
  const aiPage = await getTenantHomeLayout(tenantSlug)

  return (
    <StorefrontThemeProvider tenantSlug={tenantSlug}>
      <StorefrontBrandBackdrop>
        <div className="flex min-h-screen flex-col">
          <StorefrontHeader tenantSlug={tenantSlug} storeName={storeName} isLoggedIn={isLoggedIn} />
          <main className="flex-1">
            <CatalogListing tenantSlug={tenantSlug} aiPage={aiPage} showBrandBanner />
          </main>
          <StorefrontFooter tenantSlug={tenantSlug} storeName={storeName} />
        </div>
      </StorefrontBrandBackdrop>
    </StorefrontThemeProvider>
  )
}
