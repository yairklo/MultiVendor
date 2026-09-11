import { adminApiClient, getServerTenantSlug } from '@/lib/api/serverApiClient'
import { totalStock, isDigitalProduct } from '@/lib/stock'
import { DashboardClient } from './DashboardClient'
import type { Product } from '@/lib/types'

const VALID_RANGES = [7, 30, 90, 365] as const
export type DashboardRangeDays = (typeof VALID_RANGES)[number]
const DEFAULT_RANGE_DAYS: DashboardRangeDays = 30

function resolveRangeDays(raw: string | undefined): DashboardRangeDays {
  const parsed = Number(raw)
  return (VALID_RANGES as readonly number[]).includes(parsed) ? (parsed as DashboardRangeDays) : DEFAULT_RANGE_DAYS
}

export default async function Dashboard({
  searchParams,
}: {
  searchParams: Promise<{ days?: string }>
}) {
  const slug = await getServerTenantSlug()
  const { days: rawDays } = await searchParams
  const rangeDays = resolveRangeDays(rawDays)

  const endDate = new Date()
  const startDate = new Date(endDate)
  startDate.setDate(startDate.getDate() - rangeDays)
  const startParam = startDate.toISOString().slice(0, 10)
  const endParam = endDate.toISOString().slice(0, 10)

  const [metrics, topProductsRes, categorySalesRes, ordersRes, productsRes, reviewsRes] = await Promise.all([
    adminApiClient(`/api/v1/admin/store/${slug}/analytics?start_date=${startParam}&end_date=${endParam}`),
    adminApiClient(`/api/v1/admin/store/${slug}/analytics/top-products?start_date=${startParam}&end_date=${endParam}&limit=5`),
    adminApiClient(`/api/v1/admin/store/${slug}/analytics/sales-by-category?start_date=${startParam}&end_date=${endParam}`),
    adminApiClient(`/api/v1/admin/store/${slug}/orders`),
    adminApiClient(`/api/v1/store/${slug}/products`),
    adminApiClient(`/api/v1/admin/store/${slug}/reviews`),
  ])

  const topProducts = Array.isArray(topProductsRes) ? topProductsRes : []
  const categorySales = Array.isArray(categorySalesRes) ? categorySalesRes : []
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
      categorySales={categorySales}
      recentOrders={recentOrders}
      lowStockProducts={lowStockProducts}
      recentReviews={recentReviews}
      rangeDays={rangeDays}
    />
  )
}
