import { getCategories, getProducts } from '@/lib/api/serverApiClient'
import { CatalogListing } from '@/components/storefront/CatalogListing'

const PAGE_SIZE = 12

export default async function ShopPage({
  params,
}: {
  params: Promise<{ tenant_slug: string }>
}) {
  const { tenant_slug: tenantSlug } = await params
  const [products, categories] = await Promise.all([
    getProducts(tenantSlug, 1, PAGE_SIZE),
    getCategories(tenantSlug),
  ])

  return (
    <CatalogListing
      tenantSlug={tenantSlug}
      initialProducts={products.data}
      initialMeta={products.meta}
      initialCategories={categories}
    />
  )
}
