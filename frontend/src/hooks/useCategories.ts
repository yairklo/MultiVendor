import { useCallback } from 'react'
import { apiClient } from '@/lib/api/apiClient'
import { getCookie } from 'cookies-next'

export function useCategories() {
  const tenantSlug = getCookie('tenantSlug') || 'test-tenant'

  const fetchCategories = useCallback(async () => {
    try {
      const data = await apiClient(`/api/v1/admin/store/${tenantSlug}/categories`)
      return Array.isArray(data) ? data : (data.data || [])
    } catch (error) {
      console.error('Error fetching categories:', error)
      return []
    }
  }, [tenantSlug])

  const createCategory = async (payload: { name: Record<string, string>; slug: string }) => {
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

  return {
    fetchCategories,
    createCategory,
    deleteCategory
  }
}
