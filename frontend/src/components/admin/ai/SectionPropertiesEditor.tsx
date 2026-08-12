'use client'

import { useState } from 'react'
import { Section } from '@/lib/ai/types'
import { Sparkles } from 'lucide-react'

const FONT_FAMILIES: { label: string; value: string }[] = [
  { label: 'Default', value: '' },
  { label: 'Serif', value: 'ui-serif, Georgia, Cambria, "Times New Roman", Times, serif' },
  { label: 'Mono', value: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace' },
  { label: 'Rounded', value: '"Trebuchet MS", Verdana, ui-rounded, system-ui, sans-serif' },
]

const FONT_SIZES: { label: string; value: string }[] = [
  { label: 'Default', value: '' },
  { label: 'Small', value: '1.125rem' },
  { label: 'Medium', value: '1.5rem' },
  { label: 'Large', value: '2rem' },
  { label: 'Extra Large', value: '2.75rem' },
]

function ColorField({
  label, value, onChange, fallback,
}: { label: string; value: string; onChange: (v: string) => void; fallback: string }) {
  const swatchValue = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(value) ? value : fallback
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-semibold text-gray-700">{label}</label>
      <div className="flex items-center gap-2">
        <input
          type="color"
          aria-label={`${label} swatch`}
          className="h-9 w-9 shrink-0 cursor-pointer rounded-md border p-0.5"
          value={swatchValue}
          onChange={(e) => onChange(e.target.value)}
        />
        <input
          type="text"
          placeholder={fallback}
          className="flex-1 rounded-md border p-2 text-sm"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
    </div>
  )
}

function FontFields({
  settings, onChange,
}: { settings: Record<string, any>; onChange: (key: string, value: any) => void }) {
  return (
    <>
      <div className="flex flex-col gap-1">
        <label className="text-xs font-semibold text-gray-700">Font</label>
        <select
          className="rounded-md border p-2 text-sm"
          value={settings.font_family ?? ''}
          onChange={(e) => onChange('font_family', e.target.value)}
        >
          {FONT_FAMILIES.map((f) => (
            <option key={f.label} value={f.value}>{f.label}</option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs font-semibold text-gray-700">Heading Size</label>
        <select
          className="rounded-md border p-2 text-sm"
          value={settings.font_size ?? ''}
          onChange={(e) => onChange('font_size', e.target.value)}
        >
          {FONT_SIZES.map((f) => (
            <option key={f.label} value={f.value}>{f.label}</option>
          ))}
        </select>
      </div>
    </>
  )
}

export function SectionPropertiesEditor({
  section,
  onChange,
  onClose,
  onAskAI,
}: {
  section: Section
  onChange: (patch: Partial<Section>) => void
  onClose: () => void
  onAskAI?: (id: string, prompt: string) => void
}) {
  const [aiPrompt, setAiPrompt] = useState('')

  const handleSettingChange = (key: string, value: any) => {
    onChange({ settings: { ...section.settings, [key]: value } })
  }

  const renderFields = () => {
    switch (section.type) {
      case 'text_block':
      case 'hero_banner':
        return (
          <>
            {section.type === 'hero_banner' ? (
              <>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-gray-700">Headline</label>
                  <input
                    type="text"
                    className="rounded-md border p-2 text-sm"
                    value={section.settings.headline ?? ''}
                    onChange={(e) => handleSettingChange('headline', e.target.value)}
                  />
                </div>
                <div className="flex gap-3">
                  <div className="flex flex-1 flex-col gap-1">
                    <label className="text-xs font-semibold text-gray-700">Size</label>
                    <select
                      className="rounded-md border p-2 text-sm"
                      value={section.settings.size ?? 'medium'}
                      onChange={(e) => handleSettingChange('size', e.target.value)}
                    >
                      <option value="small">Small</option>
                      <option value="medium">Medium</option>
                      <option value="large">Large</option>
                    </select>
                  </div>
                  <div className="flex flex-1 flex-col gap-1">
                    <label className="text-xs font-semibold text-gray-700">Alignment</label>
                    <select
                      className="rounded-md border p-2 text-sm"
                      value={section.settings.alignment ?? 'center'}
                      onChange={(e) => handleSettingChange('alignment', e.target.value)}
                    >
                      <option value="left">Left</option>
                      <option value="center">Center</option>
                      <option value="right">Right</option>
                    </select>
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-gray-700">Heading</label>
                  <input
                    type="text"
                    className="rounded-md border p-2 text-sm"
                    value={section.settings.heading ?? ''}
                    onChange={(e) => handleSettingChange('heading', e.target.value)}
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-gray-700">Body</label>
                  <textarea
                    className="rounded-md border p-2 text-sm"
                    rows={4}
                    value={section.settings.body ?? ''}
                    onChange={(e) => handleSettingChange('body', e.target.value)}
                  />
                </div>
              </>
            )}
            <FontFields settings={section.settings} onChange={handleSettingChange} />
            <ColorField
              label="Background Color"
              fallback="#ffffff"
              value={section.settings.background_color ?? ''}
              onChange={(v) => handleSettingChange('background_color', v)}
            />
            <ColorField
              label="Text Color"
              fallback="#000000"
              value={section.settings.text_color ?? ''}
              onChange={(v) => handleSettingChange('text_color', v)}
            />
          </>
        )
      case 'grid_container':
      case 'two_column_layout':
        return (
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-700">Design Variant</label>
            <select
              className="rounded-md border p-2 text-sm"
              value={section.settings.design_variant ?? 'neutral'}
              onChange={(e) => handleSettingChange('design_variant', e.target.value)}
            >
              <option value="neutral">Neutral</option>
              <option value="primary">Primary</option>
              <option value="secondary">Secondary</option>
              <option value="accent">Accent</option>
              <option value="muted">Muted</option>
            </select>
          </div>
        )
      case 'product_grid':
        return (
          <>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-gray-700">Title</label>
              <input
                type="text"
                className="rounded-md border p-2 text-sm"
                value={section.settings.title ?? ''}
                onChange={(e) => handleSettingChange('title', e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-gray-700">Columns</label>
              <input
                type="number"
                min={2}
                max={4}
                className="rounded-md border p-2 text-sm"
                value={section.settings.columns ?? 3}
                onChange={(e) => handleSettingChange('columns', parseInt(e.target.value) || 3)}
              />
            </div>
          </>
        )
      default:
        return <div className="text-sm text-gray-500">Manual editing for {section.type} is coming soon. Use Ask AI below.</div>
    }
  }

  return (
    <div className="flex h-full flex-col border-l border-gray-200 bg-white">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <h3 className="font-semibold text-gray-800">Edit {section.type.replace('_', ' ')}</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">×</button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {renderFields()}

        <hr className="my-4 border-gray-200" />
        
        <div className="flex flex-col gap-2 rounded-lg border border-indigo-100 bg-indigo-50 p-4">
          <div className="flex items-center gap-2 text-indigo-700">
            <Sparkles className="h-4 w-4" />
            <h4 className="text-sm font-semibold">Ask AI to Edit</h4>
          </div>
          <p className="text-xs text-indigo-600/80">Tell the AI what you want to change about this specific section.</p>
          <div className="mt-2 flex gap-2">
            <input
              type="text"
              placeholder="e.g. Make it more professional..."
              className="flex-1 rounded-md border border-indigo-200 px-3 py-1.5 text-sm"
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && aiPrompt.trim() && onAskAI) {
                  onAskAI(section.id, aiPrompt)
                  setAiPrompt('')
                }
              }}
            />
            <button
              onClick={() => {
                if (aiPrompt.trim() && onAskAI) {
                  onAskAI(section.id, aiPrompt)
                  setAiPrompt('')
                }
              }}
              className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
