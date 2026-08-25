import { Metadata } from 'next'
import { getTenantHomeLayout } from '@/lib/api/serverApiClient'
import { CatalogListing } from '@/components/storefront/CatalogListing'

type Params = { tenant_slug: string }

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { tenant_slug } = await params
  const decodedSlug = decodeURIComponent(tenant_slug)
  const capitalizedSlug = decodedSlug.charAt(0).toUpperCase() + decodedSlug.slice(1)

  return {
    title: capitalizedSlug,
    description: `Welcome to ${capitalizedSlug} on MultiVendor`,
  }
}

export default async function StorefrontPage({
  params,
}: {
  params: Promise<{ tenant_slug: string }>
}) {
  const { tenant_slug: tenantSlug } = await params

  // The vendor's AI/CMS-managed "home" layout, if they've used the AI Layout
  // editor (or applied a premium template) — CatalogListing falls back to the
  // classic catalog listing when there is none yet (aiPage stays null), so
  // untouched stores are unaffected.
  const aiPage = await getTenantHomeLayout(tenantSlug)

  return <CatalogListing tenantSlug={tenantSlug} aiPage={aiPage} showBrandBanner />
}
