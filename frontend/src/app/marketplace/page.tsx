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

  const [productsResult, categoriesResult] = await Promise.allSettled([
    getMarketplaceProducts(currentPage, PAGE_SIZE, q || undefined, category || undefined),
    getMarketplaceCategories(),
  ])

  const productsFailed = productsResult.status === 'rejected'
  if (productsFailed) console.error('Failed to load marketplace products:', productsResult.reason)
  const products = productsResult.status === 'fulfilled' ? productsResult.value : { data: [], meta: null }
  // Categories failing just hides the filters.
  const categories = categoriesResult.status === 'fulfilled' ? categoriesResult.value : []

  return (
    <MarketplaceListing
      initialProducts={products.data}
      initialMeta={products.meta}
      initialError={productsFailed}
      initialCategories={categories}
      initialCategory={category}
    />
  )
}
