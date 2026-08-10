'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { apiClient } from '@/lib/api/apiClient'
import { getCookie } from 'cookies-next'
import { orderStatusClass, orderStatusLabel } from '@/lib/orderStatus'
import { totalStock, stockLevel, stockLevelLabel, stockLevelClass } from '@/lib/stock'

export default function Dashboard() {
  const slug = getCookie('tenantSlug') || 'test-tenant'
  const [metrics, setMetrics] = useState<any>(null)
  const [recentOrders, setRecentOrders] = useState<any[]>([])
  const [lowStockProducts, setLowStockProducts] = useState<any[]>([])

  useEffect(() => {
    apiClient(`/api/v1/admin/store/${slug}/analytics?start_date=2023-01-01&end_date=2026-12-31`)
      .then(data => setMetrics(data))
      .catch((e) => {
        console.error("Dashboard failed to load metrics", e)
      })

    apiClient(`/api/v1/admin/store/${slug}/orders`)
      .then(data => {
        const orders = Array.isArray(data) ? data : (data.data || [])
        setRecentOrders(orders.slice(0, 5))
      })
      .catch((e) => console.error("Dashboard failed to load recent orders", e))

    apiClient(`/api/v1/store/${slug}/products`)
      .then(data => {
        const products = data.data || []
        const lowStock = products
          .map((p: any) => ({ ...p, _stock: totalStock(p.variants) }))
          .filter((p: any) => Number.isFinite(p._stock) && p._stock <= 5)
          .sort((a: any, b: any) => a._stock - b._stock)
        setLowStockProducts(lowStock)
      })
      .catch((e) => console.error("Dashboard failed to load products for low-stock panel", e))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (!metrics) return <div>Loading...</div>

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <h1 className="text-3xl font-bold mb-8 text-gray-900">Admin Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-center transform hover:-translate-y-1 transition-transform">
          <h2 className="text-gray-500 font-medium mb-2 uppercase tracking-wide text-sm">Total Revenue</h2>
          <div className="text-4xl font-bold text-gray-900">${metrics.totalRevenue}</div>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-center transform hover:-translate-y-1 transition-transform">
          <h2 className="text-gray-500 font-medium mb-2 uppercase tracking-wide text-sm">AOV</h2>
          <div className="text-4xl font-bold text-gray-900">${metrics.aov}</div>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-center transform hover:-translate-y-1 transition-transform">
          <h2 className="text-gray-500 font-medium mb-2 uppercase tracking-wide text-sm">Orders Count</h2>
          <div className="text-4xl font-bold text-gray-900">{metrics.ordersCount}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-bold text-gray-900">Recent Orders</h2>
            <Link href="/admin/orders" className="text-sm text-blue-600 hover:underline">View all</Link>
          </div>
          {recentOrders.length === 0 ? (
            <p className="text-gray-500 text-sm">No orders yet.</p>
          ) : (
            <div className="space-y-3">
              {recentOrders.map(order => (
                <div key={order.id} className="flex justify-between items-center text-sm">
                  <div>
                    <div className="font-medium text-gray-900">{order.customer_name || 'Guest'}</div>
                    <div className="text-gray-500">${order.total_amount}</div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${orderStatusClass[order.status] || 'bg-gray-100 text-gray-700'}`}>
                    {orderStatusLabel[order.status] || order.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-bold text-gray-900">Low Stock</h2>
            <Link href="/admin/products" className="text-sm text-blue-600 hover:underline">View all</Link>
          </div>
          {lowStockProducts.length === 0 ? (
            <p className="text-gray-500 text-sm">Nothing running low.</p>
          ) : (
            <div className="space-y-3">
              {lowStockProducts.map((p: any) => {
                const level = stockLevel(p._stock)
                return (
                  <div key={p.id} className="flex justify-between items-center text-sm">
                    <span className="font-medium text-gray-900">
                      {typeof p.name === 'object' ? (p.name?.en || p.name?.he || 'Unnamed') : p.name}
                    </span>
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${stockLevelClass[level]}`}>
                      {p._stock} &middot; {stockLevelLabel[level]}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
