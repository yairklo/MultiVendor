'use client'

import React, { useState } from 'react'
import { apiClient } from '@/lib/api/apiClient'
import { getCookie } from 'cookies-next'

export default function SettingsPage() {
  const tenantSlug = getCookie('tenantSlug') || 'test-tenant'
  
  const [formData, setFormData] = useState({
    currency: 'USD',
    primary_color: '#3b82f6',
    default_language: 'en'
  })
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setSuccess(false)
    try {
      await apiClient(`/api/v1/admin/store/${tenantSlug}/settings`, {
        method: 'PUT',
        body: JSON.stringify(formData)
      })
      setSuccess(true)
    } catch (err: any) {
      alert(err.message || 'Failed to update settings')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Store Settings</h1>

      {success && (
        <div className="mb-6 p-4 bg-green-50 text-green-700 rounded-lg border border-green-100">
          Settings updated successfully!
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 space-y-6">
        <div>
          <label className="block text-sm font-medium mb-1">Currency</label>
          <select
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-600"
            value={formData.currency}
            onChange={e => setFormData({ ...formData, currency: e.target.value })}
          >
            <option value="USD">USD ($)</option>
            <option value="EUR">EUR (€)</option>
            <option value="GBP">GBP (£)</option>
            <option value="ILS">ILS (₪)</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-1">Primary Theme Color</label>
          <div className="flex items-center space-x-4">
            <input
              type="color"
              className="w-12 h-12 p-1 border rounded cursor-pointer"
              value={formData.primary_color}
              onChange={e => setFormData({ ...formData, primary_color: e.target.value })}
            />
            <input
              type="text"
              className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-600 uppercase"
              value={formData.primary_color}
              onChange={e => setFormData({ ...formData, primary_color: e.target.value })}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Default Language</label>
          <select
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-600"
            value={formData.default_language}
            onChange={e => setFormData({ ...formData, default_language: e.target.value })}
          >
            <option value="en">English</option>
            <option value="he">Hebrew</option>
          </select>
        </div>

        <div className="pt-4 border-t">
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-bold hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  )
}
