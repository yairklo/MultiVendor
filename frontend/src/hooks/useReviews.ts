import { apiClient } from '@/lib/api/apiClient'
import { useTenantSlug } from './useTenantSlug'

export function useReviews() {
  const tenantSlug = useTenantSlug()

  const fetchReviews = async () => {
    if (!tenantSlug) return []
    const data = await apiClient(`/api/v1/admin/store/${tenantSlug}/reviews`)
    return Array.isArray(data) ? data : (data.data || [])
  }

  const updateReviewStatus = async (reviewId: number, status: 'approved' | 'rejected') => {
    return apiClient(`/api/v1/admin/store/${tenantSlug}/reviews/${reviewId}/status?status=${status}`, {
      method: 'PATCH'
    })
  }

  return {
    fetchReviews,
    updateReviewStatus
  }
}
