import { adminApiClient } from '@/lib/api/serverApiClient'
import { OrdersClient } from './OrdersClient'
import type { PlatformOrder } from '../types'

export default async function SuperAdminOrdersPage() {
  const response = await adminApiClient('/api/v1/super-admin/orders')
  return <OrdersClient initialOrders={(response.data || []) as PlatformOrder[]} />
}
