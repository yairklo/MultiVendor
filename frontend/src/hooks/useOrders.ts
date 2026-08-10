import { apiClient } from '@/lib/api/apiClient'

export function useOrders() {
  const fetchOrders = async () => {
    const data = await apiClient('/api/v1/customer/orders')
    return data.data || []
  }

  const fetchOrder = async (orderId: number | string) => {
    return apiClient(`/api/v1/customer/orders/${orderId}`)
  }

  const cancelOrder = async (orderId: number | string) => {
    return apiClient(`/api/v1/customer/orders/${orderId}`, {
      method: 'DELETE'
    })
  }

  const payOrder = async (orderId: number | string) => {
    return apiClient(`/api/v1/customer/orders/${orderId}/pay`, {
      method: 'POST'
    })
  }

  return {
    fetchOrders,
    fetchOrder,
    cancelOrder,
    payOrder
  }
}
