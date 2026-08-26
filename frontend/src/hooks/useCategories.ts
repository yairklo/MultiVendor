import { useCallback } from 'react'
import { apiClient, ApiError } from '@/lib/api/apiClient'
import { useTenantSlug } from './useTenantSlug'

export function useCategories() {
  const tenantSlug = useTenantSlug()

  const fetchCategories = useCallback(async () => {
    if (!tenantSlug) return []
    try {
      const data = await apiClient(`/api/v1/admin/store/${tenantSlug}/categories`)
      return Array.isArray(data) ? data : (data.data || [])
    } catch (error) {
      if (!(error instanceof ApiError && (error.status === 403 || error.status === 401))) {
        console.error(`Error fetching categories (${error instanceof ApiError ? error.status : 'unknown'})`)
      }
      return []
    }
  }, [tenantSlug])

  const createCategory = async (payload: { name: Record<string, string>; slug: string }) => {
    if (!tenantSlug) throw new Error('Tenant slug is not resolved')
    return apiClient(`/api/v1/admin/store/${tenantSlug}/categories`, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  const deleteCategory = async (categoryId: number) => {
    return apiClient(`/api/v1/admin/store/${tenantSlug}/categories/${categoryId}`, {
      method: 'DELETE'
    })
  }

  const updateCategory = async (
    categoryId: number,
    payload: { name?: Record<string, string>; slug?: string; parent_id?: number | null },
  ) => {
    if (!tenantSlug) throw new Error('Tenant slug is not resolved')
    return apiClient(`/api/v1/admin/store/${tenantSlug}/categories/${categoryId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  }

  return {
    fetchCategories,
    createCategory,
    updateCategory,
    deleteCategory
  }
}
