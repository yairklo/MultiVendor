import { apiClient } from '@/lib/api/apiClient'
import { useTenantSlug } from './useTenantSlug'

export function useCoupons() {
  const tenantSlug = useTenantSlug()

  const fetchCoupons = async () => {
    if (!tenantSlug) return []
    const data = await apiClient(`/api/v1/admin/store/${tenantSlug}/coupons`)
    return Array.isArray(data) ? data : (data.data || [])
  }

  const createCoupon = async (payload: Record<string, unknown>) => {
    return apiClient(`/api/v1/admin/store/${tenantSlug}/coupons`, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  const deleteCoupon = async (couponId: number) => {
    return apiClient(`/api/v1/admin/store/${tenantSlug}/coupons/${couponId}`, {
      method: 'DELETE'
    })
  }

  const updateCoupon = async (couponId: number, payload: Record<string, unknown>) => {
    if (!tenantSlug) throw new Error('Tenant slug is not resolved')
    return apiClient(`/api/v1/admin/store/${tenantSlug}/coupons/${couponId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  }

  return {
    fetchCoupons,
    createCoupon,
    updateCoupon,
    deleteCoupon
  }
}
