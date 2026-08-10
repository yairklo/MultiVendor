import { apiClient } from '@/lib/api/apiClient'
import { getCookie } from 'cookies-next'

export function useCustomers() {
  const tenantSlug = getCookie('tenantSlug') || 'test-tenant'

  const fetchCustomers = async () => {
    const data = await apiClient(`/api/v1/admin/store/${tenantSlug}/customers`)
    return Array.isArray(data) ? data : (data.data || [])
  }

  return {
    fetchCustomers
  }
}
