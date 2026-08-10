import { apiClient } from '@/lib/api/apiClient'
import { getCookie } from 'cookies-next'

export function useReviews() {
  const tenantSlug = getCookie('tenantSlug') || 'test-tenant'

  const fetchReviews = async () => {
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
