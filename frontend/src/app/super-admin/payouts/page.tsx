import { adminApiClient } from '@/lib/api/serverApiClient'
import { PayoutsClient } from './PayoutsClient'
import type { TenantAdmin } from '../types'

export default async function SuperAdminPayoutsPage() {
  const response = await adminApiClient('/api/v1/super-admin/tenants')
  return <PayoutsClient tenants={(response.data || []) as TenantAdmin[]} />
}
