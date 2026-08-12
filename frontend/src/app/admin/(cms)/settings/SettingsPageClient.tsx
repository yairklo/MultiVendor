'use client'

import React, { useState } from 'react'
import { apiClient } from '@/lib/api/apiClient'
import { getCookie } from 'cookies-next'
import { useToast } from '@/context/ToastContext'

export function SettingsPageClient({
  initialSettings,
}: {
  initialSettings: { currency: string; primary_color: string; default_language: string }
}) {
  const tenantSlug = getCookie('tenantSlug') || 'test-tenant'
  const { showToast } = useToast()

  const [formData, setFormData] = useState(initialSettings)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await apiClient(`/api/v1/admin/store/${tenantSlug}/settings`, {
        method: 'PUT',
        body: JSON.stringify(formData)
      })
      showToast('Settings updated successfully!', 'success')
    } catch (err: any) {
      showToast(err.message || 'Failed to update settings', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Store Settings</h1>

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
