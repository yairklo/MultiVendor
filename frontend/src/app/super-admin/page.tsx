import { adminApiClient } from '@/lib/api/serverApiClient'
import { OverviewClient } from './OverviewClient'
import type { PlatformOverview } from './types'

export default async function SuperAdminPage() {
  const overview = (await adminApiClient('/api/v1/super-admin/overview')) as PlatformOverview
  return <OverviewClient overview={overview} />
}
