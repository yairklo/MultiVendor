'use client'

import { useState } from 'react'
import { LocalizedText, Section } from '@/lib/ai/types'
import { Sparkles, Plus, Trash2 } from 'lucide-react'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'

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

const ICON_NAMES = [
  'Truck', 'ShieldCheck', 'RotateCcw', 'Sparkles', 'Heart', 'Gift', 'Clock', 'Award', 'Leaf',
  'CreditCard', 'Headphones', 'PackageCheck',
]

function ColorField({
  label, value, onChange, fallback,
}: { label: string; value: string; onChange: (v: string) => void; fallback: string }) {
  const swatchValue = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(value) ? value : fallback
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-semibold text-foreground">{label}</label>
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
        <label className="text-xs font-semibold text-foreground">Font</label>
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
        <label className="text-xs font-semibold text-foreground">Heading Size</label>
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

/** Switches which language every LocalizedInput below reads/writes -- shared with
 * useStorefrontTheme().lang, so flipping a tab also re-renders the live preview
 * canvas alongside this panel in that language (WYSIWYG: you edit what you see). */
function LanguageTabs({
  languages, active, onChange,
}: { languages: string[]; active: string; onChange: (lang: string) => void }) {
  if (languages.length <= 1) return null
  return (
    <div className="mb-1 flex gap-1 rounded-md bg-muted p-1">
      {languages.map((l) => (
        <button
          key={l}
          type="button"
          onClick={() => onChange(l as 'en' | 'he')}
          className={`flex-1 rounded px-2 py-1 text-xs font-semibold uppercase transition-colors ${
            active === l ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  )
}

/** A section saved before this feature shipped has a plain string here, not {lang: text} --
 * mirrors the backend's own auto-upgrade (store_page_service._localize_value): treat it as
 * that string duplicated under every supported language, both for display and as the base an
 * edit merges into. Without this, reading a legacy field shows blank, and editing one would
 * spread a string's characters into numeric object keys instead of setting a language key. */
function normalizeLocalized(value: unknown, supportedLanguages: string[]): LocalizedText {
  if (typeof value === 'string') {
    return Object.fromEntries(supportedLanguages.map((l) => [l, value]))
  }
  if (value && typeof value === 'object') return value as LocalizedText
  return {}
}

/** A text field whose value is {lang: text} instead of a plain string -- always reads/writes
 * only the currently active tab's language, preserving whatever the other languages hold. */
function LocalizedInput({
  label, value, lang, supportedLanguages, onChange, multiline, placeholder,
}: {
  label: string
  value: unknown
  lang: string
  supportedLanguages: string[]
  onChange: (next: LocalizedText) => void
  multiline?: boolean
  placeholder?: string
}) {
  const normalized = normalizeLocalized(value, supportedLanguages)
  const current = normalized[lang] ?? ''
  const commonProps = {
    className: 'rounded-md border p-2 text-sm',
    value: current,
    placeholder,
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      onChange({ ...normalized, [lang]: e.target.value }),
  }
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-semibold text-foreground">{label}</label>
      {multiline ? <textarea rows={3} {...commonProps} /> : <input type="text" {...commonProps} />}
    </div>
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
  const { lang: editingLang, setLang: setEditingLang, supportedLanguages } = useStorefrontTheme()

  const handleSettingChange = (key: string, value: any) => {
    onChange({ settings: { ...section.settings, [key]: value } })
  }

  const handleItemsChange = (arrayKey: string, items: any[]) => {
    handleSettingChange(arrayKey, items)
  }

  const languageTabs = (
    <LanguageTabs languages={supportedLanguages} active={editingLang} onChange={setEditingLang} />
  )

  const renderFields = () => {
    switch (section.type) {
      case 'text_block':
      case 'hero_banner':
        return (
          <>
            {languageTabs}
            {section.type === 'hero_banner' ? (
              <>
                <LocalizedInput
                  label="Headline"
                  value={section.settings.headline}
                  lang={editingLang} supportedLanguages={supportedLanguages}
                  onChange={(v) => handleSettingChange('headline', v)}
                />
                <div className="flex gap-3">
                  <div className="flex flex-1 flex-col gap-1">
                    <label className="text-xs font-semibold text-foreground">Size</label>
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
                    <label className="text-xs font-semibold text-foreground">Alignment</label>
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
                <LocalizedInput
                  label="Heading"
                  value={section.settings.heading}
                  lang={editingLang} supportedLanguages={supportedLanguages}
                  onChange={(v) => handleSettingChange('heading', v)}
                />
                <LocalizedInput
                  label="Body"
                  value={section.settings.body}
                  lang={editingLang} supportedLanguages={supportedLanguages}
                  onChange={(v) => handleSettingChange('body', v)}
                  multiline
                />
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
          <>
            {section.type === 'grid_container' && (
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-foreground">Columns</label>
                <select
                  className="rounded-md border p-2 text-sm"
                  value={section.settings.columns ?? 3}
                  onChange={(e) => handleSettingChange('columns', parseInt(e.target.value, 10))}
                >
                  <option value={2}>2</option>
                  <option value={3}>3</option>
                  <option value={4}>4</option>
                </select>
              </div>
            )}
            {section.type === 'two_column_layout' && (
              <p className="text-xs text-muted-foreground">Drag the divider between the two columns on the canvas to resize them.</p>
            )}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-foreground">Design Variant</label>
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
          </>
        )
      case 'product_grid':
        return (
          <>
            {languageTabs}
            <LocalizedInput
              label="Title"
              value={section.settings.title}
              lang={editingLang} supportedLanguages={supportedLanguages}
              onChange={(v) => handleSettingChange('title', v)}
            />
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-foreground">Columns</label>
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
      case 'video_embed':
        return (
          <>
            {languageTabs}
            <LocalizedInput
              label="Title"
              value={section.settings.title}
              lang={editingLang} supportedLanguages={supportedLanguages}
              onChange={(v) => handleSettingChange('title', v)}
            />
            <label className="flex items-center gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                checked={!!section.settings.autoplay}
                onChange={(e) => handleSettingChange('autoplay', e.target.checked)}
              />
              Autoplay
            </label>
          </>
        )
      case 'gallery': {
        const images: string[] = Array.isArray(section.settings.images) ? section.settings.images : []
        return (
          <>
            {languageTabs}
            <LocalizedInput
              label="Title (optional)"
              value={section.settings.title}
              lang={editingLang} supportedLanguages={supportedLanguages}
              onChange={(v) => handleSettingChange('title', v)}
            />
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-foreground">Layout</label>
              <select
                className="rounded-md border p-2 text-sm"
                value={section.settings.layout ?? 'grid'}
                onChange={(e) => handleSettingChange('layout', e.target.value)}
              >
                <option value="grid">Grid</option>
                <option value="carousel">Carousel</option>
              </select>
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-foreground">Image URLs</label>
              {images.map((url, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    type="text"
                    className="flex-1 rounded-md border p-2 text-sm"
                    value={url}
                    onChange={(e) => {
                      const next = [...images]
                      next[i] = e.target.value
                      handleItemsChange('images', next)
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => handleItemsChange('images', images.filter((_, idx) => idx !== i))}
                    className="rounded-md border p-2 text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => handleItemsChange('images', [...images, ''])}
                className="flex items-center justify-center gap-1 rounded-md border border-dashed p-2 text-xs text-muted-foreground hover:border-muted-foreground"
              >
                <Plus className="h-3.5 w-3.5" /> Add image URL
              </button>
            </div>
          </>
        )
      }
      case 'button_group': {
        const buttons: any[] = Array.isArray(section.settings.buttons) ? section.settings.buttons : []
        const updateButton = (i: number, patch: Record<string, any>) => {
          const next = buttons.map((b, idx) => (idx === i ? { ...b, ...patch } : b))
          handleItemsChange('buttons', next)
        }
        return (
          <>
            {languageTabs}
            <div className="flex flex-col gap-3">
              {buttons.map((button, i) => (
                <div key={i} className="flex flex-col gap-2 rounded-md border p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-muted-foreground">Button {i + 1}</span>
                    <button
                      type="button"
                      onClick={() => handleItemsChange('buttons', buttons.filter((_, idx) => idx !== i))}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <LocalizedInput
                    label="Label"
                    value={button.label}
                    lang={editingLang} supportedLanguages={supportedLanguages}
                    onChange={(v) => updateButton(i, { label: v })}
                  />
                  <select
                    className="rounded-md border p-2 text-sm"
                    value={button.variant ?? 'primary'}
                    onChange={(e) => updateButton(i, { variant: e.target.value })}
                  >
                    <option value="primary">Primary</option>
                    <option value="secondary">Secondary</option>
                    <option value="outline">Outline</option>
                  </select>
                  <p className="text-xs text-muted-foreground">
                    Action target ({button.actionType ?? 'not set'}) — edit via Ask AI below.
                  </p>
                </div>
              ))}
              <button
                type="button"
                onClick={() =>
                  handleItemsChange('buttons', [
                    ...buttons,
                    { label: {}, variant: 'primary', actionType: 'NAVIGATE', actionPayload: { href: '/shop' } },
                  ])
                }
                className="flex items-center justify-center gap-1 rounded-md border border-dashed p-2 text-xs text-muted-foreground hover:border-muted-foreground"
              >
                <Plus className="h-3.5 w-3.5" /> Add button
              </button>
            </div>
          </>
        )
      }
      case 'testimonials': {
        const items: any[] = Array.isArray(section.settings.items) ? section.settings.items : []
        const updateItem = (i: number, patch: Record<string, any>) => {
          const next = items.map((it, idx) => (idx === i ? { ...it, ...patch } : it))
          handleItemsChange('items', next)
        }
        return (
          <>
            {languageTabs}
            <LocalizedInput
              label="Title (optional)"
              value={section.settings.title}
              lang={editingLang} supportedLanguages={supportedLanguages}
              onChange={(v) => handleSettingChange('title', v)}
            />
            <div className="flex flex-col gap-3">
              {items.map((item, i) => (
                <div key={i} className="flex flex-col gap-2 rounded-md border p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-muted-foreground">Testimonial {i + 1}</span>
                    <button
                      type="button"
                      onClick={() => handleItemsChange('items', items.filter((_, idx) => idx !== i))}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <LocalizedInput label="Quote" value={item.quote} lang={editingLang} supportedLanguages={supportedLanguages} onChange={(v) => updateItem(i, { quote: v })} multiline />
                  <LocalizedInput label="Author" value={item.author} lang={editingLang} supportedLanguages={supportedLanguages} onChange={(v) => updateItem(i, { author: v })} />
                  <LocalizedInput label="Role (optional)" value={item.role} lang={editingLang} supportedLanguages={supportedLanguages} onChange={(v) => updateItem(i, { role: v })} />
                </div>
              ))}
              <button
                type="button"
                onClick={() => handleItemsChange('items', [...items, { quote: {}, author: {}, role: {} }])}
                className="flex items-center justify-center gap-1 rounded-md border border-dashed p-2 text-xs text-muted-foreground hover:border-muted-foreground"
              >
                <Plus className="h-3.5 w-3.5" /> Add testimonial
              </button>
            </div>
          </>
        )
      }
      case 'feature_highlights': {
        const items: any[] = Array.isArray(section.settings.items) ? section.settings.items : []
        const updateItem = (i: number, patch: Record<string, any>) => {
          const next = items.map((it, idx) => (idx === i ? { ...it, ...patch } : it))
          handleItemsChange('items', next)
        }
        return (
          <>
            {languageTabs}
            <LocalizedInput
              label="Title (optional)"
              value={section.settings.title}
              lang={editingLang} supportedLanguages={supportedLanguages}
              onChange={(v) => handleSettingChange('title', v)}
            />
            <div className="flex flex-col gap-3">
              {items.map((item, i) => (
                <div key={i} className="flex flex-col gap-2 rounded-md border p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-muted-foreground">Highlight {i + 1}</span>
                    <button
                      type="button"
                      onClick={() => handleItemsChange('items', items.filter((_, idx) => idx !== i))}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <select
                    className="rounded-md border p-2 text-sm"
                    value={item.icon ?? 'Sparkles'}
                    onChange={(e) => updateItem(i, { icon: e.target.value })}
                  >
                    {ICON_NAMES.map((name) => (
                      <option key={name} value={name}>{name}</option>
                    ))}
                  </select>
                  <LocalizedInput label="Title" value={item.title} lang={editingLang} supportedLanguages={supportedLanguages} onChange={(v) => updateItem(i, { title: v })} />
                  <LocalizedInput label="Text" value={item.text} lang={editingLang} supportedLanguages={supportedLanguages} onChange={(v) => updateItem(i, { text: v })} multiline />
                </div>
              ))}
              <button
                type="button"
                onClick={() => handleItemsChange('items', [...items, { icon: 'Sparkles', title: {}, text: {} }])}
                className="flex items-center justify-center gap-1 rounded-md border border-dashed p-2 text-xs text-muted-foreground hover:border-muted-foreground"
              >
                <Plus className="h-3.5 w-3.5" /> Add highlight
              </button>
            </div>
          </>
        )
      }
      case 'table': {
        const headers: LocalizedText[] = Array.isArray(section.settings.headers) ? section.settings.headers : []
        const rows: LocalizedText[][] = Array.isArray(section.settings.rows) ? section.settings.rows : []
        const setHeaderCell = (i: number, v: LocalizedText) => {
          const next = headers.map((h, idx) => (idx === i ? v : h))
          handleSettingChange('headers', next)
        }
        const setRowCell = (r: number, c: number, v: LocalizedText) => {
          const next = rows.map((row, ri) => (ri === r ? row.map((cell, ci) => (ci === c ? v : cell)) : row))
          handleSettingChange('rows', next)
        }
        const addColumn = () => {
          handleSettingChange('headers', [...headers, {}])
          handleSettingChange('rows', rows.map((row) => [...row, {}]))
        }
        const removeColumn = (c: number) => {
          handleSettingChange('headers', headers.filter((_, i) => i !== c))
          handleSettingChange('rows', rows.map((row) => row.filter((_, i) => i !== c)))
        }
        const addRow = () => handleSettingChange('rows', [...rows, headers.map(() => ({}))])
        const removeRow = (r: number) => handleSettingChange('rows', rows.filter((_, i) => i !== r))
        return (
          <>
            {languageTabs}
            <LocalizedInput
              label="Title (optional)"
              value={section.settings.title}
              lang={editingLang} supportedLanguages={supportedLanguages}
              onChange={(v) => handleSettingChange('title', v)}
            />
            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-foreground">Columns</label>
              {headers.map((header, c) => (
                <div key={c} className="flex gap-2">
                  <div className="flex-1">
                    <LocalizedInput
                      label={`Column ${c + 1} header`}
                      value={header}
                      lang={editingLang}
                      supportedLanguages={supportedLanguages}
                      onChange={(v) => setHeaderCell(c, v)}
                    />
                  </div>
                  <button type="button" onClick={() => removeColumn(c)} className="mt-5 h-fit rounded-md border p-2 text-muted-foreground hover:text-destructive">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={addColumn}
                className="flex items-center justify-center gap-1 rounded-md border border-dashed p-2 text-xs text-muted-foreground hover:border-muted-foreground"
              >
                <Plus className="h-3.5 w-3.5" /> Add column
              </button>
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-foreground">Rows</label>
              {rows.map((row, r) => (
                <div key={r} className="flex flex-col gap-1 rounded-md border p-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Row {r + 1}</span>
                    <button type="button" onClick={() => removeRow(r)} className="text-muted-foreground hover:text-destructive">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  {headers.map((_, c) => (
                    <LocalizedInput
                      key={c}
                      label={`Column ${c + 1}`}
                      value={row[c]}
                      lang={editingLang}
                      supportedLanguages={supportedLanguages}
                      onChange={(v) => setRowCell(r, c, v)}
                    />
                  ))}
                </div>
              ))}
              <button
                type="button"
                onClick={addRow}
                disabled={headers.length === 0}
                className="flex items-center justify-center gap-1 rounded-md border border-dashed p-2 text-xs text-muted-foreground hover:border-muted-foreground disabled:opacity-50"
              >
                <Plus className="h-3.5 w-3.5" /> Add row
              </button>
            </div>
          </>
        )
      }
      default:
        return <div className="text-sm text-muted-foreground">Manual editing for {section.type} is coming soon. Use Ask AI below.</div>
    }
  }

  return (
    <div className="flex h-full flex-col border-l border-border bg-card">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <h3 className="font-semibold text-foreground">Edit {section.type.replace('_', ' ')}</h3>
        <button onClick={onClose} className="text-muted-foreground transition-colors hover:text-foreground">×</button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {renderFields()}

        <hr className="my-4 border-border" />

        <div className="flex flex-col gap-2 rounded-lg border border-primary/20 bg-primary/5 p-4">
          <div className="flex items-center gap-2 text-primary">
            <Sparkles className="h-4 w-4" />
            <h4 className="text-sm font-semibold">Ask AI to Edit</h4>
          </div>
          <p className="text-xs text-primary/80">Tell the AI what you want to change about this specific section.</p>
          <div className="mt-2 flex gap-2">
            <input
              type="text"
              placeholder="e.g. Make it more professional..."
              className="flex-1 rounded-md border border-primary/30 px-3 py-1.5 text-sm"
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
              className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
