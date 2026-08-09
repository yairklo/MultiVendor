'use client'

import React, { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api/apiClient'

export default function Dashboard() {
  const [metrics, setMetrics] = useState<any>(null)

  useEffect(() => {
    apiClient('/api/v1/admin/metrics')
      .then(data => setMetrics(data))
      .catch(() => {})
  }, [])

  if (!metrics) return <div>Loading...</div>

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <h1 className="text-3xl font-bold mb-8 text-gray-900">Admin Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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
    </div>
  )
}
