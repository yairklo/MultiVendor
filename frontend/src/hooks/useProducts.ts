import { apiClient } from '@/lib/api/apiClient'
import { useTenantSlug } from './useTenantSlug'

export function useProducts() {
  const tenantSlug = useTenantSlug()

  const fetchProducts = async (page = 1, pageSize = 20, search = '', categoryId: number | null = null) => {
    if (!tenantSlug) return { data: [], meta: null }
    try {
      let url = `/api/v1/store/${tenantSlug}/products?page=${page}&page_size=${pageSize}`
      if (search) url += `&q=${encodeURIComponent(search)}`
      if (categoryId) url += `&category_id=${categoryId}`
      
      const data = await apiClient(url)
      return { data: data.data || [], meta: data.meta }
    } catch (error) {
      console.error('Error fetching products:', error)
      return { data: [], meta: null }
    }
  }

  const fetchProduct = async (productId: number | string) => {
    if (!tenantSlug) throw new Error('Tenant slug is not resolved')
    return apiClient(`/api/v1/admin/store/${tenantSlug}/products/${productId}`)
  }

  const createProduct = async (payload: Record<string, unknown>) => {
    if (!tenantSlug) throw new Error('Tenant slug is not resolved')
    return apiClient(`/api/v1/admin/store/${tenantSlug}/products`, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  const updateProduct = async (productId: number, payload: Record<string, unknown>) => {
    if (!tenantSlug) throw new Error('Tenant slug is not resolved')
    return apiClient(`/api/v1/admin/store/${tenantSlug}/products/${productId}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    })
  }

  const deleteProduct = async (productId: number) => {
    if (!tenantSlug) throw new Error('Tenant slug is not resolved')
    return apiClient(`/api/v1/admin/store/${tenantSlug}/products/${productId}`, {
      method: 'DELETE'
    })
  }

  const updateVariant = async (variantId: number, payload: Record<string, unknown>) => {
    if (!tenantSlug) throw new Error('Tenant slug is not resolved')
    return apiClient(`/api/v1/admin/store/${tenantSlug}/variants/${variantId}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    })
  }

  return {
    fetchProducts,
    fetchProduct,
    createProduct,
    updateProduct,
    deleteProduct,
    updateVariant
  }
}
