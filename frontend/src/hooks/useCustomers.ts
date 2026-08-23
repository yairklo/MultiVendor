import { apiClient } from '@/lib/api/apiClient'
import { useTenantSlug } from './useTenantSlug'

export function useCustomers() {
  const tenantSlug = useTenantSlug()

  const fetchCustomers = async () => {
    if (!tenantSlug) return []
    const data = await apiClient(`/api/v1/admin/store/${tenantSlug}/customers`)
    return Array.isArray(data) ? data : (data.data || [])
  }

  return {
    fetchCustomers
  }
}
