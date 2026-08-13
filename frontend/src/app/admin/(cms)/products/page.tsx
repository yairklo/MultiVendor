import { getServerTenantSlug, getProducts } from '@/lib/api/serverApiClient'
import { ProductsPageClient } from './ProductsPageClient'

export default async function ProductsPage() {
  const tenantSlug = await getServerTenantSlug()
  const { data, meta } = await getProducts(tenantSlug, 1, 20)

  return <ProductsPageClient initialProducts={data} initialMeta={meta} />
}
