import { adminApiClient, getServerTenantSlug } from '@/lib/api/serverApiClient'
import { CustomersPageClient } from './CustomersPageClient'

export default async function CustomersPage() {
  const tenantSlug = await getServerTenantSlug()
  const data = await adminApiClient(`/api/v1/admin/store/${tenantSlug}/customers`)
  const customers = Array.isArray(data) ? data : (data.data || [])

  return <CustomersPageClient initialCustomers={customers} />
}
