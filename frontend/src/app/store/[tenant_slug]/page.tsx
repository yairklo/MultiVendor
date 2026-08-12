import { getTenantHomeLayout } from '@/lib/api/serverApiClient'
import { CatalogListing } from '@/components/storefront/CatalogListing'

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

  return <CatalogListing tenantSlug={tenantSlug} aiPage={aiPage} />
}
