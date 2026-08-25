'use client'

import React, { useMemo, useState } from 'react'
import { LayoutTemplate, Plus } from 'lucide-react'
import { apiClient } from '@/lib/api/apiClient'
import { useToast } from '@/context/ToastContext'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

export type StorefrontTemplateAdmin = {
  id: number
  template_key: string
  name: string
  tagline: string
  swatch_json: { bg: string; text: string; accent: string }
  pages_json: Record<string, unknown>
  display_order: number
  is_active: boolean
  is_builtin: boolean
}

const STARTER_PAGES = {
  home: {
    title: 'Home',
    background_color: '#ffffff',
    text_color: '#111827',
    sections: [
      { type: 'hero_banner', settings: { headline: 'Welcome', size: 'large', alignment: 'center' } },
    ],
  },
  about: {
    title: 'About',
    background_color: '#ffffff',
    text_color: '#111827',
    sections: [
      { type: 'text_block', settings: { heading: 'About us', body: 'Tell your story.' } },
    ],
  },
  contact: {
    title: 'Contact',
    background_color: '#ffffff',
    text_color: '#111827',
    sections: [
      { type: 'text_block', settings: { heading: 'Get in touch', body: 'hello@yourstore.com' } },
    ],
  },
}

type FormState = {
  template_key: string
  name: string
  tagline: string
  bg: string
  text: string
  accent: string
  display_order: string
  pages_json: string
}

const EMPTY_FORM: FormState = {
  template_key: '',
  name: '',
  tagline: '',
  bg: '#ffffff',
  text: '#111827',
  accent: '#6366f1',
  display_order: '10',
  pages_json: JSON.stringify(STARTER_PAGES, null, 2),
}

function formFromTemplate(template: StorefrontTemplateAdmin): FormState {
  return {
    template_key: template.template_key,
    name: template.name,
    tagline: template.tagline,
    bg: template.swatch_json?.bg || '#ffffff',
    text: template.swatch_json?.text || '#111827',
    accent: template.swatch_json?.accent || '#6366f1',
    display_order: String(template.display_order ?? 0),
    pages_json: JSON.stringify(template.pages_json ?? STARTER_PAGES, null, 2),
  }
}

export function TemplatesClient({ initialTemplates }: { initialTemplates: StorefrontTemplateAdmin[] }) {
  const { showToast } = useToast()
  const [templates, setTemplates] = useState(initialTemplates)
  const [editingKey, setEditingKey] = useState<string | 'new' | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [togglingKey, setTogglingKey] = useState<string | null>(null)

  const isCreate = editingKey === 'new'
  const editingTemplate = useMemo(
    () => (typeof editingKey === 'string' && editingKey !== 'new'
      ? templates.find((t) => t.template_key === editingKey)
      : undefined),
    [editingKey, templates],
  )

  async function reload() {
    const response = await apiClient('/api/v1/super-admin/storefront-templates')
    setTemplates(response.data || [])
  }

  function openCreate() {
    setForm(EMPTY_FORM)
    setEditingKey('new')
  }

  function openEdit(template: StorefrontTemplateAdmin) {
    setForm(formFromTemplate(template))
    setEditingKey(template.template_key)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    let pages_json: Record<string, unknown>
    try {
      pages_json = JSON.parse(form.pages_json)
    } catch {
      showToast('pages_json must be valid JSON', 'error')
      return
    }
    if (!pages_json || typeof pages_json !== 'object' || Array.isArray(pages_json)) {
      showToast('pages_json must be an object of page keys', 'error')
      return
    }

    const payload = {
      name: form.name.trim(),
      tagline: form.tagline.trim(),
      swatch_json: { bg: form.bg, text: form.text, accent: form.accent },
      pages_json,
      display_order: Number(form.display_order) || 0,
    }

    setSaving(true)
    try {
      if (isCreate) {
        await apiClient('/api/v1/super-admin/storefront-templates', {
          method: 'POST',
          body: JSON.stringify({ ...payload, template_key: form.template_key.trim() }),
        })
        showToast('Template created', 'success')
      } else if (editingKey) {
        await apiClient(`/api/v1/super-admin/storefront-templates/${editingKey}`, {
          method: 'PUT',
          body: JSON.stringify(payload),
        })
        showToast('Template saved', 'success')
      }
      setEditingKey(null)
      await reload()
    } catch (err: any) {
      showToast(err.message || 'Failed to save template', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function toggleActive(template: StorefrontTemplateAdmin) {
    setTogglingKey(template.template_key)
    try {
      await apiClient(`/api/v1/super-admin/storefront-templates/${template.template_key}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !template.is_active }),
      })
      await reload()
      showToast(template.is_active ? 'Template deactivated' : 'Template activated', 'success')
    } catch (err: any) {
      showToast(err.message || 'Failed to update template', 'error')
    } finally {
      setTogglingKey(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-heading text-3xl font-bold tracking-tight">Storefront templates</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Catalog shown to sellers. Built-in Aurora, Atelier, and Nova can be turned off, not deleted.
          </p>
        </div>
        <Button type="button" onClick={openCreate}>
          <Plus className="h-4 w-4" />
          New template
        </Button>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_420px]">
        <Card className="overflow-hidden py-0 shadow-sm">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Template</TableHead>
                <TableHead>Order</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {templates.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="py-12 text-center text-muted-foreground">
                    <LayoutTemplate className="mx-auto mb-2 h-8 w-8 opacity-40" />
                    No templates yet.
                  </TableCell>
                </TableRow>
              )}
              {templates.map((template) => (
                <TableRow key={template.template_key} className="hover:bg-muted/50">
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div
                        className="h-10 w-10 shrink-0 rounded-lg border border-border shadow-inner"
                        style={{ background: template.swatch_json?.bg, color: template.swatch_json?.accent }}
                        aria-hidden
                      />
                      <div>
                        <div className="flex items-center gap-2 font-semibold">
                          {template.name}
                          {template.is_builtin && <Badge variant="secondary">Built-in</Badge>}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {template.template_key} · {template.tagline}
                        </div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{template.display_order}</TableCell>
                  <TableCell>
                    <Badge variant={template.is_active ? 'success' : 'outline'}>
                      {template.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="secondary" size="sm" onClick={() => openEdit(template)}>
                        Edit
                      </Button>
                      <Button
                        variant={template.is_active ? 'outline' : 'default'}
                        size="sm"
                        disabled={togglingKey === template.template_key}
                        onClick={() => toggleActive(template)}
                      >
                        {template.is_active ? 'Deactivate' : 'Activate'}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>

        {editingKey && (
          <Card className="h-fit p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-bold">
              {isCreate ? 'New template' : `Edit ${editingTemplate?.name || editingKey}`}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="template_key">Key</Label>
                <Input
                  id="template_key"
                  value={form.template_key}
                  onChange={(e) => setForm((prev) => ({ ...prev, template_key: e.target.value }))}
                  placeholder="lumen"
                  required
                  disabled={!isCreate}
                  pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="template_name">Name</Label>
                <Input
                  id="template_name"
                  value={form.name}
                  onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="template_tagline">Tagline</Label>
                <Input
                  id="template_tagline"
                  value={form.tagline}
                  onChange={(e) => setForm((prev) => ({ ...prev, tagline: e.target.value }))}
                  required
                />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="swatch_bg">Background</Label>
                  <Input id="swatch_bg" type="color" value={form.bg} onChange={(e) => setForm((prev) => ({ ...prev, bg: e.target.value }))} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="swatch_text">Text</Label>
                  <Input id="swatch_text" type="color" value={form.text} onChange={(e) => setForm((prev) => ({ ...prev, text: e.target.value }))} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="swatch_accent">Accent</Label>
                  <Input id="swatch_accent" type="color" value={form.accent} onChange={(e) => setForm((prev) => ({ ...prev, accent: e.target.value }))} />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="display_order">Display order</Label>
                <Input
                  id="display_order"
                  type="number"
                  value={form.display_order}
                  onChange={(e) => setForm((prev) => ({ ...prev, display_order: e.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="pages_json">pages_json</Label>
                <textarea
                  id="pages_json"
                  value={form.pages_json}
                  onChange={(e) => setForm((prev) => ({ ...prev, pages_json: e.target.value }))}
                  rows={14}
                  className="w-full rounded-lg border border-input bg-transparent px-2.5 py-2 font-mono text-xs leading-relaxed outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  required
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setEditingKey(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={saving}>
                  {saving ? 'Saving…' : isCreate ? 'Create template' : 'Save changes'}
                </Button>
              </div>
            </form>
          </Card>
        )}
      </div>
    </div>
  )
}
