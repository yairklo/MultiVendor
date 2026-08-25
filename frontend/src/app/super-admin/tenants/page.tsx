import { adminApiClient } from '@/lib/api/serverApiClient'
import { TenantsClient } from './TenantsClient'
import type { SubscriptionPlanAdmin, TenantAdmin } from '../types'

export default async function SuperAdminTenantsPage() {
  const [tenantsRes, plansRes] = await Promise.all([
    adminApiClient('/api/v1/super-admin/tenants'),
    adminApiClient('/api/v1/super-admin/plans'),
  ])
  return (
    <TenantsClient
      initialTenants={(tenantsRes.data || []) as TenantAdmin[]}
      plans={(plansRes.data || []) as SubscriptionPlanAdmin[]}
    />
  )
}
