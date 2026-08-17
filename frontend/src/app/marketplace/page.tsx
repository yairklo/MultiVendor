import { getMarketplaceProducts } from '@/lib/api/serverApiClient'
import { MarketplaceListing } from '@/components/marketplace/MarketplaceListing'

const PAGE_SIZE = 12

export const metadata = {
  title: 'Marketplace',
}

export default async function MarketplacePage() {
  const products = await getMarketplaceProducts(1, PAGE_SIZE)

  return <MarketplaceListing initialProducts={products.data} initialMeta={products.meta} />
}
