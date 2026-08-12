import { adminApiClient, getServerTenantSlug } from '@/lib/api/serverApiClient'
import { ReviewsPageClient } from './ReviewsPageClient'

export default async function ReviewsPage() {
  const tenantSlug = await getServerTenantSlug()
  const data = await adminApiClient(`/api/v1/admin/store/${tenantSlug}/reviews`)
  const reviews = Array.isArray(data) ? data : (data.data || [])

  return <ReviewsPageClient initialReviews={reviews} />
}
