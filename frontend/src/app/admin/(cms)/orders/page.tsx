'use client'

import React, { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api/apiClient'
import { getCookie } from 'cookies-next'
import { orderStatusClass, orderStatusLabel } from '@/lib/orderStatus'
import { useToast } from '@/context/ToastContext'

const MANUAL_STATUSES = ['pending', 'processing', 'completed', 'cancelled']

export default function OrdersPage() {
  const { showToast } = useToast()
  const [orders, setOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [updatingId, setUpdatingId] = useState<number | null>(null)
  const tenantSlug = getCookie('tenantSlug') || 'test-tenant'

  useEffect(() => {
    fetchOrders()
  }, [])

  const fetchOrders = async () => {
    try {
      const data = await apiClient(`/api/v1/admin/store/${tenantSlug}/orders`)
      setOrders(data.items || data || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const res = await fetch(`http://localhost:8000/api/v1/admin/store/${tenantSlug}/reports/export?report_type=orders`, {
        headers: { Authorization: `Bearer ${getCookie('token')}` },
      })
      if (!res.ok) throw new Error('Export failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'orders.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Failed to export orders CSV:', e)
      showToast('Failed to export orders.', 'error')
    } finally {
      setExporting(false)
    }
  }

  const handleStatusChange = async (orderId: number, status: string) => {
    setUpdatingId(orderId)
    try {
      await apiClient(`/api/v1/admin/store/${tenantSlug}/orders/${orderId}/status?status=${status}`, {
        method: 'PATCH',
      })
      await fetchOrders()
      showToast(`Order #${orderId} updated to ${orderStatusLabel[status] || status}`, 'success')
    } catch (e) {
      console.error('Failed to update order status:', e)
      showToast('Failed to update order status.', 'error')
    } finally {
      setUpdatingId(null)
    }
  }

  if (loading) return <div className="text-gray-500">Loading orders...</div>

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Store Orders</h1>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="px-4 py-2 bg-gray-800 text-white rounded-lg font-medium hover:bg-gray-900 disabled:opacity-50"
        >
          {exporting ? 'Exporting...' : 'Export CSV'}
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100">
              <th className="p-4 font-semibold text-gray-600">Order ID</th>
              <th className="p-4 font-semibold text-gray-600">Customer</th>
              <th className="p-4 font-semibold text-gray-600">Total</th>
              <th className="p-4 font-semibold text-gray-600">Status</th>
            </tr>
          </thead>
          <tbody>
            {orders.length === 0 && (
              <tr>
                <td colSpan={4} className="p-8 text-center text-gray-500">No orders found.</td>
              </tr>
            )}
            {orders.map(order => (
              <tr key={order.id} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="p-4 font-medium">#{order.id}</td>
                <td className="p-4">
                  <div className="font-medium text-gray-900">{order.customer_name || 'Guest'}</div>
                  {order.customer_email && (
                    <div className="text-sm text-gray-500">{order.customer_email}</div>
                  )}
                </td>
                <td className="p-4">${order.total_amount}</td>
                <td className="p-4">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                      orderStatusClass[order.status] || 'bg-gray-100 text-gray-700'
                    }`}>
                      {orderStatusLabel[order.status] || order.status || 'Pending'}
                    </span>
                    <select
                      aria-label={`Change status for order ${order.id}`}
                      value={MANUAL_STATUSES.includes(order.status) ? order.status : ''}
                      disabled={updatingId === order.id}
                      onChange={e => handleStatusChange(order.id, e.target.value)}
                      className="text-xs border rounded px-1 py-1 text-gray-600"
                    >
                      {!MANUAL_STATUSES.includes(order.status) && (
                        <option value="" disabled>{orderStatusLabel[order.status] || order.status}</option>
                      )}
                      {MANUAL_STATUSES.map(s => (
                        <option key={s} value={s}>{orderStatusLabel[s]}</option>
                      ))}
                    </select>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
