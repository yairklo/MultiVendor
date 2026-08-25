import { adminApiClient } from '@/lib/api/serverApiClient'
import { PlansClient } from './PlansClient'
import type { SubscriptionPlanAdmin } from '../types'

export default async function SuperAdminPlansPage() {
  const response = await adminApiClient('/api/v1/super-admin/plans')
  return <PlansClient plans={(response.data || []) as SubscriptionPlanAdmin[]} />
}
