import { apiClient } from '@/lib/api/apiClient'
import { getCookie } from 'cookies-next'

export function useProducts() {
  const tenantSlug = getCookie('tenantSlug') || 'test-tenant'

  const fetchProducts = async () => {
    try {
      const data = await apiClient(`/api/v1/store/${tenantSlug}/products`)
      return data.data || []
    } catch (error) {
      console.error('Error fetching products:', error)
      return []
    }
  }

  const fetchProduct = async (productId: number | string) => {
    return apiClient(`/api/v1/admin/store/${tenantSlug}/products/${productId}`)
  }

  const createProduct = async (payload: any) => {
    return apiClient(`/api/v1/admin/store/${tenantSlug}/products`, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  const updateProduct = async (productId: number, payload: any) => {
    return apiClient(`/api/v1/admin/store/${tenantSlug}/products/${productId}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    })
  }

  const deleteProduct = async (productId: number) => {
    return apiClient(`/api/v1/admin/store/${tenantSlug}/products/${productId}`, {
      method: 'DELETE'
    })
  }

  const updateVariant = async (variantId: number, payload: any) => {
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
