'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getCookie } from 'cookies-next'
import { apiClient } from '@/lib/api/apiClient'

export default function SuperAdminPage() {
  const router = useRouter()
  const [authorized, setAuthorized] = useState(false)
  const [tenants, setTenants] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getCookie('token')) {
      router.replace('/admin/login')
      return
    }
    setAuthorized(true)
  }, [router])

  useEffect(() => {
    if (!authorized) return
    fetchTenants()
  }, [authorized])

  const fetchTenants = async () => {
    try {
      const response = await apiClient('/api/v1/super-admin/tenants')
      // backend returns { data: [...] } based on TenantListResponse
      setTenants(response.data || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const toggleStatus = async (tenantId: string | number, currentStatus: string) => {
    const newStatus = currentStatus === 'active' ? 'suspended' : 'active'
    try {
      await apiClient(`/api/v1/super-admin/tenants/${tenantId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus })
      })
      fetchTenants()
    } catch (e) {
      alert('Failed to update status')
    }
  }

  if (!authorized) return null
  if (loading) return <div className="p-8 text-center text-gray-500">Loading registry...</div>

  return (
    <div className="p-8 bg-gray-50 min-h-screen text-gray-900">
      <h1 className="text-3xl font-bold mb-8">Platform Super Admin</h1>
      
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100">
              <th className="p-4 font-semibold text-gray-600">Tenant Name & Domain</th>
              <th className="p-4 font-semibold text-gray-600">Creation Date</th>
              <th className="p-4 font-semibold text-gray-600">Products (Used / Max)</th>
              <th className="p-4 font-semibold text-gray-600">Status</th>
              <th className="p-4 font-semibold text-gray-600 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tenants.length === 0 && (
              <tr>
                <td colSpan={5} className="p-8 text-center text-gray-500">No tenants registered yet.</td>
              </tr>
            )}
            {tenants.map(tenant => (
              <tr key={tenant.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                <td className="p-4">
                  <div className="font-bold">{tenant.name}</div>
                  <div className="text-sm text-gray-500">{tenant.slug}</div>
                </td>
                <td className="p-4 text-gray-600">
                  {new Date(tenant.created_at).toLocaleDateString()}
                </td>
                <td className="p-4">
                  {tenant.current_products_count || 0} / {tenant.max_products || '∞'}
                  <div className="text-xs text-gray-400">Tier: {tenant.subscription_tier}</div>
                </td>
                <td className="p-4">
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    tenant.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {tenant.status.toUpperCase()}
                  </span>
                </td>
                <td className="p-4 text-right">
                  <button 
                    onClick={() => toggleStatus(tenant.id, tenant.status)}
                    className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-800 rounded-lg text-sm font-medium transition-colors"
                  >
                    {tenant.status === 'active' ? 'Suspend' : 'Activate'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
