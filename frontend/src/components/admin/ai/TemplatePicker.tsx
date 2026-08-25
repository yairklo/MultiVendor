"use client"

import React, { useState } from 'react'
import { LayoutTemplate, X } from 'lucide-react'
import { useUiLocale } from '@/context/UiLocaleContext'

export function TemplatePicker({
  templates,
  onApply,
  isApplying,
}: {
  templates: any[]
  onApply: (key: string) => void
  isApplying: boolean
}) {
  const { t } = useUiLocale()
  const [isOpen, setIsOpen] = useState(false)

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
          <div className="w-full max-w-4xl overflow-hidden rounded-xl bg-card shadow-2xl">
            <div className="flex items-center justify-between border-b px-6 py-4">
              <h2 className="text-xl font-bold">{t('aiLayout.chooseTemplate')}</h2>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
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
                      className="flex h-32 items-end p-4"
                      style={{ background: template.swatch.bg, color: template.swatch.text }}
                    >
                      <span className="text-lg font-bold" style={{ color: template.swatch.accent }}>
                        {template.name}
                      </span>
                    </div>
                    <div className="flex flex-1 flex-col gap-3 p-4">
                      <p className="flex-1 text-sm text-muted-foreground">{template.tagline}</p>
                      <button
                        type="button"
                        onClick={() => {
                          onApply(template.key)
                          setIsOpen(false)
                        }}
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
          </div>
        </div>
      )}
    </>
  )
}
