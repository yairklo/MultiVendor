import { adminApiClient, getServerTenantSlug } from '@/lib/api/serverApiClient'
import { totalStock, isDigitalProduct } from '@/lib/stock'
import { DashboardClient } from './DashboardClient'
import type { Product } from '@/lib/types'

export default async function Dashboard() {
  const slug = await getServerTenantSlug()

  const [metrics, topProductsRes, ordersRes, productsRes, reviewsRes] = await Promise.all([
    adminApiClient(`/api/v1/admin/store/${slug}/analytics?start_date=2023-01-01&end_date=2026-12-31`),
    adminApiClient(`/api/v1/admin/store/${slug}/analytics/top-products?start_date=2023-01-01&end_date=2026-12-31&limit=5`),
    adminApiClient(`/api/v1/admin/store/${slug}/orders`),
    adminApiClient(`/api/v1/store/${slug}/products`),
    adminApiClient(`/api/v1/admin/store/${slug}/reviews`),
  ])

  const topProducts = Array.isArray(topProductsRes) ? topProductsRes : []
  const recentOrders = (Array.isArray(ordersRes) ? ordersRes : (ordersRes.data || [])).slice(0, 5)

  const products: Product[] = productsRes.data || []
  const lowStockProducts = products
    .map((p) => ({ ...p, _stock: totalStock(p.variants) }))
    .filter((p) => !isDigitalProduct(p) && Number.isFinite(p._stock) && p._stock <= 10)
    .sort((a, b) => a._stock - b._stock)
    .slice(0, 5)

  const recentReviews = Array.isArray(reviewsRes) ? reviewsRes.slice(0, 5) : []

  return (
    <DashboardClient
      metrics={metrics}
      topProducts={topProducts}
      recentOrders={recentOrders}
      lowStockProducts={lowStockProducts}
      recentReviews={recentReviews}
    />
  )
}
