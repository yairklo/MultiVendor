import { getMarketplaceProducts, getMarketplaceCategories } from '@/lib/api/serverApiClient'
import { MarketplaceListing } from '@/components/marketplace/MarketplaceListing'

const PAGE_SIZE = 12

export const metadata = {
  title: 'Marketplace',
}

interface PageProps {
  searchParams: Promise<{
    q?: string
    category?: string
    page?: string
  }>
}

export default async function MarketplacePage({ searchParams }: PageProps) {
  const params = await searchParams
  const currentPage = Number(params?.page) || 1
  const category = params?.category || ''
  const q = params?.q || ''

  const [products, categories] = await Promise.all([
    getMarketplaceProducts(currentPage, PAGE_SIZE, q || undefined, category || undefined),
    getMarketplaceCategories(),
  ])

  return (
    <MarketplaceListing
      initialProducts={products.data}
      initialMeta={products.meta}
      initialCategories={categories}
      initialCategory={category}
    />
  )
}
