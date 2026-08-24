"use client"

import React, { useState } from 'react'
import { LayoutTemplate, X } from 'lucide-react'

export function TemplatePicker({
  templates,
  onApply,
  isApplying,
}: {
  templates: any[]
  onApply: (key: string) => void
  isApplying: boolean
}) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-sm font-semibold text-foreground transition-colors hover:bg-muted"
      >
        <LayoutTemplate className="h-4 w-4" />
        Templates
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-4xl overflow-hidden rounded-xl bg-card shadow-2xl">
            <div className="flex items-center justify-between border-b px-6 py-4">
              <h2 className="text-xl font-bold">Choose a Starting Template</h2>
              <button onClick={() => setIsOpen(false)} className="text-muted-foreground transition-colors hover:text-foreground">
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="grid grid-cols-1 gap-6 p-6 md:grid-cols-3 bg-muted max-h-[70vh] overflow-y-auto">
              {templates.length === 0 ? (
                <div className="col-span-3 py-12 text-center text-muted-foreground">Loading templates...</div>
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
                        className="flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
                      >
                        {isApplying ? 'Applying...' : 'Apply Template to Drafts'}
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
