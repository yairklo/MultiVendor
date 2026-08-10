'use client'

import React, { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api/apiClient'
import { getCookie } from 'cookies-next'
import { orderStatusClass, orderStatusLabel } from '@/lib/orderStatus'

export default function OrdersPage() {
  const [orders, setOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
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

  if (loading) return <div className="text-gray-500">Loading orders...</div>

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Store Orders</h1>

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
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                    orderStatusClass[order.status] || 'bg-gray-100 text-gray-700'
                  }`}>
                    {orderStatusLabel[order.status] || order.status || 'Pending'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
