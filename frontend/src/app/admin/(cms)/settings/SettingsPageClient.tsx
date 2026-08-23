'use client'

import React, { useState } from 'react'
import { apiClient } from '@/lib/api/apiClient'
import { useToast } from '@/context/ToastContext'
import { useTenantSlug } from '@/hooks/useTenantSlug'

export interface StoreSettings {
  currency: string
  logo_url: string
  banner_url: string
  support_email: string
  supported_languages: string[]
  default_language: string
  review_moderation_enabled: boolean
  allow_unverified_reviews: boolean
  custom_css: string
  template_key: string
}

const AVAILABLE_LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'he', label: 'Hebrew' },
  { code: 'fr', label: 'French' },
  { code: 'es', label: 'Spanish' },
  { code: 'ar', label: 'Arabic' }
]

export function SettingsPageClient({
  initialSettings,
}: {
  initialSettings: StoreSettings
}) {
  const tenantSlug = useTenantSlug()
  const { showToast } = useToast()

  const [formData, setFormData] = useState<StoreSettings>(initialSettings)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    
    // Clean up empty strings to null so Pydantic validation (like EmailStr) doesn't fail on ""
    const payload = {
      ...formData,
      support_email: formData.support_email || null,
      logo_url: formData.logo_url || null,
      banner_url: formData.banner_url || null,
      custom_css: formData.custom_css || null,
      template_key: formData.template_key || null,
    }

    if (!tenantSlug) {
      showToast('Store is not resolved yet. Please sign in again.', 'error')
      return
    }

    try {
      await apiClient(`/api/v1/admin/store/${tenantSlug}/settings`, {
        method: 'PUT',
        body: JSON.stringify(payload)
      })
      showToast('Settings updated successfully!', 'success')
    } catch (err: any) {
      showToast(err.message || 'Failed to update settings', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleLanguageToggle = (langCode: string) => {
    const current = formData.supported_languages
    const isSelected = current.includes(langCode)
    
    let newLangs = isSelected ? current.filter(l => l !== langCode) : [...current, langCode]
    if (newLangs.length === 0) newLangs = ['en'] // ensure at least one
    
    let newDefault = formData.default_language
    if (!newLangs.includes(newDefault)) {
      newDefault = newLangs[0]
    }

    setFormData({
      ...formData,
      supported_languages: newLangs,
      default_language: newDefault
    })
  }

  return (
    <div className="max-w-4xl mx-auto pb-12">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Store Settings</h1>

      <form onSubmit={handleSubmit} className="space-y-8">
        
        {/* General Store Details */}
        <section className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h2 className="text-xl font-semibold mb-6 pb-2 border-b">General Details</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-700">Logo URL</label>
              <input
                type="url"
                placeholder="https://..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-blue-600"
                value={formData.logo_url}
                onChange={e => setFormData({ ...formData, logo_url: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-700">Banner URL</label>
              <input
                type="url"
                placeholder="https://..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-blue-600"
                value={formData.banner_url}
                onChange={e => setFormData({ ...formData, banner_url: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-700">Support Email</label>
              <input
                type="email"
                placeholder="support@store.com"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-blue-600"
                value={formData.support_email}
                onChange={e => setFormData({ ...formData, support_email: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-700">Currency</label>
              <select
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-blue-600"
                value={formData.currency}
                onChange={e => setFormData({ ...formData, currency: e.target.value })}
              >
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
                <option value="ILS">ILS (₪)</option>
              </select>
            </div>
          </div>
        </section>

        {/* Localization Settings */}
        <section className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h2 className="text-xl font-semibold mb-6 pb-2 border-b">Localization</h2>
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-3 text-gray-700">Supported Languages</label>
              <div className="flex flex-wrap gap-4">
                {AVAILABLE_LANGUAGES.map(lang => (
                  <label key={lang.code} className="flex items-center space-x-2 cursor-pointer bg-gray-50 px-3 py-2 rounded-lg border">
                    <input
                      type="checkbox"
                      className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                      checked={formData.supported_languages.includes(lang.code)}
                      onChange={() => handleLanguageToggle(lang.code)}
                    />
                    <span className="text-sm font-medium text-gray-700">{lang.label}</span>
                  </label>
                ))}
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-700">Default Language</label>
              <select
                className="w-full md:w-1/2 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-blue-600"
                value={formData.default_language}
                onChange={e => setFormData({ ...formData, default_language: e.target.value })}
              >
                {AVAILABLE_LANGUAGES.filter(l => formData.supported_languages.includes(l.code)).map(lang => (
                  <option key={lang.code} value={lang.code}>{lang.label}</option>
                ))}
              </select>
            </div>
          </div>
        </section>

        {/* Review Settings */}
        <section className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h2 className="text-xl font-semibold mb-6 pb-2 border-b">Reviews & Moderation</h2>
          <div className="space-y-4">
            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                className="w-5 h-5 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                checked={formData.review_moderation_enabled}
                onChange={e => setFormData({ ...formData, review_moderation_enabled: e.target.checked })}
              />
              <div>
                <span className="block text-sm font-medium text-gray-900">Enable Review Moderation</span>
                <span className="block text-sm text-gray-500">Require admin approval before reviews are published.</span>
              </div>
            </label>

            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                className="w-5 h-5 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                checked={formData.allow_unverified_reviews}
                onChange={e => setFormData({ ...formData, allow_unverified_reviews: e.target.checked })}
              />
              <div>
                <span className="block text-sm font-medium text-gray-900">Allow Unverified Reviews</span>
                <span className="block text-sm text-gray-500">Allow users who haven't purchased the item to leave reviews.</span>
              </div>
            </label>
          </div>
        </section>

        {/* Advanced Settings */}
        <section className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h2 className="text-xl font-semibold mb-6 pb-2 border-b">Advanced</h2>
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-700">Template Key</label>
              <input
                type="text"
                placeholder="default"
                className="w-full md:w-1/2 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-blue-600"
                value={formData.template_key}
                onChange={e => setFormData({ ...formData, template_key: e.target.value })}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-700">Custom CSS</label>
              <textarea
                className="w-full h-32 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-blue-600 font-mono text-sm"
                placeholder="/* Add custom CSS here */"
                value={formData.custom_css}
                onChange={e => setFormData({ ...formData, custom_css: e.target.value })}
              />
            </div>
          </div>
        </section>

        <div className="flex justify-end pt-4">
          <button
            type="submit"
            disabled={loading}
            className="px-8 py-3 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 focus:ring-4 focus:ring-blue-200 transition-colors disabled:opacity-50"
          >
            {loading ? 'Saving Changes...' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  )
}
