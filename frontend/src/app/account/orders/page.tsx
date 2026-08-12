'use client'

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getCookie } from 'cookies-next'
import { useOrders } from '@/hooks/useOrders'
import { orderStatusClass as statusClass, orderStatusLabel as statusLabel } from '@/lib/orderStatus'
import { useToast } from '@/context/ToastContext'
import { useConfirm } from '@/context/ConfirmContext'

export default function MyOrdersPage() {
  const router = useRouter()
  const { fetchOrders, cancelOrder, payOrder } = useOrders()
  const { showToast } = useToast()
  const { confirm } = useConfirm()
  const [orders, setOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!getCookie('token')) {
      router.replace('/login')
      return
    }
    loadOrders()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadOrders = async () => {
    setLoading(true)
    try {
      const data = await fetchOrders()
      setOrders(data)
    } catch (e: any) {
      setError(e.message || 'Failed to load orders')
    } finally {
      setLoading(false)
    }
  }

  const handlePay = async (orderId: number) => {
    setBusyId(orderId)
    setError('')
    try {
      await payOrder(orderId)
      await loadOrders()
      showToast('Payment successful', 'success')
    } catch (e: any) {
      showToast(e.message || 'Payment failed', 'error')
    } finally {
      setBusyId(null)
    }
  }

  const handleCancel = async (orderId: number) => {
    const ok = await confirm({
      title: 'Cancel this order?',
      confirmLabel: 'Cancel Order',
      cancelLabel: 'Keep Order',
      variant: 'destructive',
    })
    if (!ok) return
    setBusyId(orderId)
    setError('')
    try {
      await cancelOrder(orderId)
      await loadOrders()
      showToast('Order cancelled', 'success')
    } catch (e: any) {
      showToast(e.message || 'Failed to cancel order', 'error')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-gray-50 min-h-screen text-gray-900">
      <h1 className="text-3xl font-bold mb-8 border-b pb-4">My Orders</h1>

      {error && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">{error}</div>
      )}

      {loading ? (
        <div className="text-gray-500">Loading your orders...</div>
      ) : orders.length === 0 ? (
        <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-100 text-center text-gray-500">
          You haven&apos;t placed any orders yet.
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map(order => {
            const canPay = order.status === 'pending_payment'
            const canCancel = order.status === 'pending' || order.status === 'pending_payment'
            return (
              <div key={order.id} data-testid="order-card" className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div className="font-bold">#{order.order_number}</div>
                    <div className="text-sm text-gray-500">{new Date(order.created_at).toLocaleString()}</div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${statusClass[order.status] || 'bg-gray-100 text-gray-700'}`}>
                    {statusLabel[order.status] || order.status}
                  </span>
                </div>

                <div className="space-y-1 mb-3 text-sm text-gray-700">
                  {order.items?.map((item: any) => (
                    <div key={item.id} className="flex justify-between">
                      <span>{item.product_name} &times; {item.quantity}</span>
                      <span>${Number(item.unit_price * item.quantity).toFixed(2)}</span>
                    </div>
                  ))}
                </div>

                <div className="flex justify-between items-center border-t pt-3">
                  <span className="font-bold">Total: ${Number(order.total_amount).toFixed(2)}</span>
                  <div className="flex gap-2">
                    {canCancel && (
                      <button
                        onClick={() => handleCancel(order.id)}
                        disabled={busyId === order.id}
                        className="px-4 py-2 text-red-600 border border-red-200 rounded-lg font-medium hover:bg-red-50 disabled:opacity-50"
                      >
                        Cancel
                      </button>
                    )}
                    {canPay && (
                      <button
                        onClick={() => handlePay(order.id)}
                        disabled={busyId === order.id}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
                      >
                        {busyId === order.id ? 'Processing...' : 'Pay Now'}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
