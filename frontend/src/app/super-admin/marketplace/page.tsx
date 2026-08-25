import { adminApiClient } from '@/lib/api/serverApiClient'
import { MarketplaceClient } from './MarketplaceClient'
import type { TenantAdmin } from '../types'

export default async function SuperAdminMarketplacePage() {
  const response = await adminApiClient('/api/v1/super-admin/tenants')
  return <MarketplaceClient initialTenants={(response.data || []) as TenantAdmin[]} />
}
