import { adminApiClient } from '@/lib/api/serverApiClient'
import { SuperAdminClient } from './SuperAdminClient'

// Unauthenticated requests never reach this page — proxy.ts middleware
// (matcher `/super-admin/:path*`) redirects to /admin/login before render.
export default async function SuperAdminPage() {
  const response = await adminApiClient('/api/v1/super-admin/tenants')
  const tenants = response.data || []

  return <SuperAdminClient initialTenants={tenants} />
}
