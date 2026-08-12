import { adminApiClient, getServerTenantSlug } from '@/lib/api/serverApiClient'
import { OrdersPageClient } from './OrdersPageClient'

export default async function OrdersPage() {
  const tenantSlug = await getServerTenantSlug()
  const data = await adminApiClient(`/api/v1/admin/store/${tenantSlug}/orders`)
  const orders = data.items || data || []

  return <OrdersPageClient initialOrders={orders} />
}
