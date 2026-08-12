import { adminApiClient, getServerTenantSlug } from '@/lib/api/serverApiClient'
import { CouponsPageClient } from './CouponsPageClient'

export default async function CouponsPage() {
  const tenantSlug = await getServerTenantSlug()
  const data = await adminApiClient(`/api/v1/admin/store/${tenantSlug}/coupons`)
  const coupons = Array.isArray(data) ? data : (data.data || [])

  return <CouponsPageClient initialCoupons={coupons} />
}
