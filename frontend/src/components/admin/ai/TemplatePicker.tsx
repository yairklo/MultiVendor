"use client"

import React, { useState } from 'react'
import { LayoutTemplate, X } from 'lucide-react'
import { useUiLocale } from '@/context/UiLocaleContext'
import type { StorefrontTemplateMeta } from '@/lib/ai/types'

const PREVIEW_PAGES = ['home', 'about', 'contact'] as const

function TemplatePagePreview({
  pageKey,
  swatch,
}: {
  pageKey: string
  swatch: { bg?: string; text?: string; accent?: string }
}) {
  const bg = swatch?.bg || '#f8f8f8'
  const text = swatch?.text || '#111827'
  const accent = swatch?.accent || '#6366f1'

  return (
    <div
      data-testid={`template-page-preview-${pageKey}`}
      className="overflow-hidden rounded-md border border-black/10 shadow-sm"
      style={{ background: bg, color: text }}
    >
      <div className="px-1.5 py-1 text-[10px] font-semibold uppercase tracking-wide opacity-70">
        {pageKey}
      </div>
      <div className="space-y-1 p-1.5 pt-0">
        <div className="h-3.5 rounded-sm" style={{ background: accent, opacity: 0.9 }} />
        <div className="h-1.5 w-4/5 rounded-sm" style={{ background: text, opacity: 0.18 }} />
        <div className="grid grid-cols-3 gap-1">
          <div className="h-4 rounded-sm" style={{ background: text, opacity: 0.1 }} />
          <div className="h-4 rounded-sm" style={{ background: text, opacity: 0.1 }} />
          <div className="h-4 rounded-sm" style={{ background: text, opacity: 0.1 }} />
        </div>
      </div>
    </div>
  )
}

export function TemplatePicker({
  templates,
  onApply,
  isApplying,
}: {
  templates: StorefrontTemplateMeta[]
  onApply: (key: string) => void
  isApplying: boolean
}) {
  const { t } = useUiLocale()
  const [isOpen, setIsOpen] = useState(false)
  const [pendingKey, setPendingKey] = useState<string | null>(null)

  const pendingTemplate = templates.find((template) => template.key === pendingKey)

  function closePicker() {
    setIsOpen(false)
    setPendingKey(null)
  }

  function confirmApply() {
    if (!pendingKey) return
    const key = pendingKey
    setPendingKey(null)
    setIsOpen(false)
    onApply(key)
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-sm font-semibold text-foreground transition-all duration-150 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.98]"
      >
        <LayoutTemplate className="h-4 w-4" />
        {t('aiLayout.templates')}
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="relative w-full max-w-4xl overflow-hidden rounded-xl bg-card shadow-2xl">
            <div className="flex items-center justify-between border-b px-6 py-4">
              <h2 className="text-xl font-bold">{t('aiLayout.chooseTemplate')}</h2>
              <button
                type="button"
                onClick={closePicker}
                aria-label={t('aiLayout.close')}
                className="rounded-md p-1 text-muted-foreground transition-all duration-150 hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.98]"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="grid max-h-[70vh] grid-cols-1 gap-6 overflow-y-auto bg-muted p-6 md:grid-cols-3">
              {templates.length === 0 ? (
                <div className="col-span-3 py-12 text-center text-muted-foreground">{t('aiLayout.loadingTemplates')}</div>
              ) : (
                templates.map((template) => (
                  <div key={template.key} className="flex flex-col overflow-hidden rounded-xl border border-border bg-card shadow-sm">
                    <div
                      className="flex h-20 items-end p-4"
                      style={{ background: template.swatch.bg, color: template.swatch.text }}
                    >
                      <span className="text-lg font-bold" style={{ color: template.swatch.accent }}>
                        {template.name}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-1.5 px-3 pt-3">
                      {PREVIEW_PAGES.map((pageKey) => (
                        <TemplatePagePreview key={pageKey} pageKey={pageKey} swatch={template.swatch} />
                      ))}
                    </div>
                    <div className="flex flex-1 flex-col gap-3 p-4">
                      <p className="flex-1 text-sm text-muted-foreground">{template.tagline}</p>
                      <button
                        type="button"
                        onClick={() => setPendingKey(template.key)}
                        disabled={isApplying}
                        className="flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-all duration-150 hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100"
                      >
                        {isApplying ? t('aiLayout.applyingTemplate') : t('aiLayout.applyTemplateToDrafts')}
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {pendingKey && (
              <div
                className="absolute inset-0 z-10 flex items-center justify-center bg-black/40 p-4"
                data-testid="template-apply-confirm"
              >
                <div
                  role="dialog"
                  aria-modal="true"
                  aria-labelledby="template-confirm-title"
                  className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-2xl"
                >
                  <h3 id="template-confirm-title" className="text-lg font-bold text-foreground">
                    {t('aiLayout.applyTemplate')}
                  </h3>
                  <p className="mt-2 text-sm text-muted-foreground">{t('aiLayout.applyTemplateDesc')}</p>
                  <p className="mt-3 text-sm font-medium text-foreground">
                    {pendingTemplate?.name ? `${pendingTemplate.name} — ` : ''}
                    home / about / contact
                  </p>
                  <div className="mt-5 flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setPendingKey(null)}
                      className="rounded-lg border border-border bg-background px-3 py-1.5 text-sm font-semibold transition-all duration-150 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.98]"
                    >
                      {t('confirm.cancel')}
                    </button>
                    <button
                      type="button"
                      onClick={confirmApply}
                      disabled={isApplying}
                      className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground transition-all duration-150 hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.98] disabled:opacity-50"
                    >
                      {t('aiLayout.applyTemplateBtn')}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
