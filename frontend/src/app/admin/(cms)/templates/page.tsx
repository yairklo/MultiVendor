'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { getCookie } from 'cookies-next'
import { Check, Sparkles } from 'lucide-react'
import { apiClient } from '@/lib/api/apiClient'
import { useToast } from '@/context/ToastContext'
import { useConfirm } from '@/context/ConfirmContext'

interface StorefrontTemplateSummary {
  key: string
  name: string
  tagline: string
  swatch: { bg: string; text: string; accent: string }
}

/** apiClient always rejects with an ApiError/Error (both carry .message), but a fetch can also
 * reject with something else entirely (e.g. a raw string) — narrow before touching .message
 * instead of assuming the shape with `any`. */
function getErrorMessage(err: unknown, fallback: string): string {
  return err instanceof Error && err.message ? err.message : fallback
}

export default function StorefrontTemplatesPage() {
  const tenantSlug = String(getCookie('tenantSlug') || 'test-tenant')
  const { showToast } = useToast()
  const { confirm } = useConfirm()

  const [templates, setTemplates] = useState<StorefrontTemplateSummary[]>([])
  const [activeKey, setActiveKey] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [applyingKey, setApplyingKey] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      apiClient(`/api/v1/admin/store/${tenantSlug}/ai/templates`),
      apiClient(`/api/v1/store/${tenantSlug}/config`),
    ])
      .then(([templateList, config]) => {
        setTemplates(templateList)
        setActiveKey(config.template_key ?? null)
      })
      .catch((err) => showToast(getErrorMessage(err, 'Failed to load templates'), 'error'))
      .finally(() => setLoading(false))
    // showToast is stable (useCallback in ToastProvider) — safe to depend on directly.
  }, [tenantSlug, showToast])

  const handleApply = async (template: StorefrontTemplateSummary) => {
    const isSwitch = !!activeKey && activeKey !== template.key
    const ok = await confirm({
      title: `Use the "${template.name}" template?`,
      description: isSwitch
        ? 'This replaces your current Home, About, and Contact pages — including any of your own edits — and publishes them immediately.'
        : 'This sets up Home, About, and Contact pages for your store and publishes them immediately. You can customize everything afterwards.',
      confirmLabel: 'Use this template',
      variant: isSwitch ? 'destructive' : 'default',
    })
    if (!ok) return

    setApplyingKey(template.key)
    try {
      await apiClient(`/api/v1/admin/store/${tenantSlug}/ai/templates/${template.key}/apply`, { method: 'POST' })
      setActiveKey(template.key)
      showToast(`"${template.name}" is now live on your storefront.`, 'success')
    } catch (err) {
      showToast(getErrorMessage(err, 'Failed to apply template'), 'error')
    } finally {
      setApplyingKey(null)
    }
  }

  if (loading) return <div className="p-6 text-gray-500">Loading templates…</div>

  return (
    <div className="max-w-5xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Storefront Templates</h1>
          <p className="text-gray-500">Pick a premium starting point for your storefront, then customize it however you like.</p>
        </div>
        <Link
          href="/admin/ai-layout"
          className="flex items-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <Sparkles className="h-4 w-4" />
          Customize with AI
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {templates.map((template) => {
          const isActive = activeKey === template.key
          return (
            <div key={template.key} className="flex flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
              <div
                className="flex h-32 items-end p-4"
                style={{ background: template.swatch.bg, color: template.swatch.text }}
              >
                <span className="text-lg font-bold" style={{ color: template.swatch.accent }}>
                  {template.name}
                </span>
              </div>
              <div className="flex flex-1 flex-col gap-3 p-4">
                <p className="flex-1 text-sm text-gray-600">{template.tagline}</p>
                <button
                  type="button"
                  onClick={() => handleApply(template)}
                  disabled={applyingKey === template.key || isActive}
                  className={`flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed ${
                    isActive
                      ? 'bg-green-50 text-green-700'
                      : 'bg-gray-900 text-white hover:bg-gray-800 disabled:opacity-50'
                  }`}
                >
                  {isActive && <Check className="h-4 w-4" />}
                  {isActive ? 'Active template' : applyingKey === template.key ? 'Applying…' : 'Use this template'}
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
