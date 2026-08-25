'use client'

import React, { useMemo, useState } from 'react'
import { ChevronDown, ChevronUp, Plus, Trash2 } from 'lucide-react'
import { apiClient } from '@/lib/api/apiClient'
import { useToast } from '@/context/ToastContext'
import { useTenantSlug } from '@/hooks/useTenantSlug'
import { useUiLocale } from '@/context/UiLocaleContext'
import { ImageUploadField } from '@/components/upload/ImageUploadField'
import {
  DEFAULT_NAV_ITEMS,
  StoreNavItem,
  effectiveNavItems,
  resolveNavLabel,
} from '@/lib/storefront-nav'
import {
  SUGGESTED_LANGUAGES,
  isValidLangCode,
  languageDisplayName,
  normalizeLangCode,
} from '@/lib/languages'

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
  nav_items: StoreNavItem[] | null
}

export function SettingsPageClient({
  initialSettings,
}: {
  initialSettings: StoreSettings
}) {
  const tenantSlug = useTenantSlug()
  const { showToast } = useToast()
  const { t, locale } = useUiLocale()

  const [formData, setFormData] = useState<StoreSettings>({
    ...initialSettings,
    nav_items: effectiveNavItems(initialSettings.nav_items),
  })
  const [loading, setLoading] = useState(false)
  const [langQuery, setLangQuery] = useState('')
  const [customLabel, setCustomLabel] = useState('')
  const [customHref, setCustomHref] = useState('')

  const navItems = formData.nav_items ?? DEFAULT_NAV_ITEMS
  const langs = formData.supported_languages.length ? formData.supported_languages : ['he']

  const languageSuggestions = useMemo(() => {
    const q = langQuery.trim().toLowerCase()
    const pool = SUGGESTED_LANGUAGES.filter((l) => !formData.supported_languages.includes(l.code))
    if (!q) return pool.slice(0, 12)
    return pool.filter((l) => {
      const name = languageDisplayName(l.code, locale).toLowerCase()
      return l.code.includes(q) || name.includes(q)
    }).slice(0, 12)
  }, [langQuery, formData.supported_languages, locale])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    const payload = {
      ...formData,
      support_email: formData.support_email || null,
      logo_url: formData.logo_url || null,
      banner_url: formData.banner_url || null,
      custom_css: formData.custom_css || null,
      template_key: formData.template_key || null,
      nav_items: navItems,
    }

    if (!tenantSlug) {
      showToast(t('settings.storeUnresolved'), 'error')
      setLoading(false)
      return
    }

    try {
      await apiClient(`/api/v1/admin/store/${tenantSlug}/settings`, {
        method: 'PUT',
        body: JSON.stringify(payload)
      })
      showToast(t('settings.saved'), 'success')
    } catch (err: any) {
      showToast(err.message || t('settings.saveFailed'), 'error')
    } finally {
      setLoading(false)
    }
  }

  const addLanguage = (code: string) => {
    const normalized = normalizeLangCode(code).toLowerCase()
    if (!isValidLangCode(normalized)) {
      showToast(t('settings.invalidLang'), 'error')
      return
    }
    if (formData.supported_languages.includes(normalized)) {
      showToast(t('settings.alreadyAdded'), 'error')
      return
    }
    setFormData({
      ...formData,
      supported_languages: [...formData.supported_languages, normalized],
    })
    setLangQuery('')
  }

  const removeLanguage = (code: string) => {
    let next = formData.supported_languages.filter((l) => l !== code)
    if (next.length === 0) next = ['he']
    const defaultLanguage = next.includes(formData.default_language) ? formData.default_language : next[0]
    setFormData({ ...formData, supported_languages: next, default_language: defaultLanguage })
  }

  const updateNavItem = (index: number, patch: Partial<StoreNavItem>) => {
    const next = navItems.map((item, i) => (i === index ? { ...item, ...patch } : item))
    setFormData({ ...formData, nav_items: next })
  }

  const moveNavItem = (index: number, dir: -1 | 1) => {
    const target = index + dir
    if (target < 0 || target >= navItems.length) return
    const next = [...navItems]
    const [removed] = next.splice(index, 1)
    next.splice(target, 0, removed)
    setFormData({ ...formData, nav_items: next })
  }

  const removeNavItem = (index: number) => {
    setFormData({ ...formData, nav_items: navItems.filter((_, i) => i !== index) })
  }

  const addCustomNav = () => {
    const label = customLabel.trim()
    const href = customHref.trim()
    if (!label || !href) return
    const id = `custom-${Date.now()}`
    const labelMap: Record<string, string> = {}
    for (const lang of langs) labelMap[lang] = label
    setFormData({
      ...formData,
      nav_items: [...navItems, { id, enabled: true, kind: 'custom', href, label: labelMap }],
    })
    setCustomLabel('')
    setCustomHref('')
  }

  return (
    <div className="max-w-4xl mx-auto pb-12">
      <h1 className="text-3xl font-bold text-foreground mb-8 font-heading">{t('settings.title')}</h1>

      <form onSubmit={handleSubmit} className="space-y-8">
        <section className="bg-card p-6 rounded-xl shadow-sm border border-border">
          <h2 className="text-xl font-semibold mb-1 pb-2 border-b border-border">{t('settings.branding')}</h2>
          <p className="text-sm text-muted-foreground mt-3 mb-6">{t('settings.brandingHint')}</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <ImageUploadField
                id="logo-upload"
                label={t('settings.logo')}
                hint={t('settings.logoHint')}
                value={formData.logo_url}
                onChange={(url) => setFormData({ ...formData, logo_url: url })}
              />
              <input
                type="url"
                placeholder={t('settings.orPasteUrl')}
                className="w-full px-4 py-2 border border-input rounded-lg bg-background focus:ring-2 focus:ring-ring"
                value={formData.logo_url}
                onChange={(e) => setFormData({ ...formData, logo_url: e.target.value })}
              />
            </div>
            <div className="space-y-3">
              <ImageUploadField
                id="banner-upload"
                label={t('settings.banner')}
                hint={t('settings.bannerHint')}
                value={formData.banner_url}
                onChange={(url) => setFormData({ ...formData, banner_url: url })}
              />
              <input
                type="url"
                placeholder={t('settings.orPasteUrl')}
                className="w-full px-4 py-2 border border-input rounded-lg bg-background focus:ring-2 focus:ring-ring"
                value={formData.banner_url}
                onChange={(e) => setFormData({ ...formData, banner_url: e.target.value })}
              />
            </div>
          </div>
        </section>

        <section className="bg-card p-6 rounded-xl shadow-sm border border-border">
          <h2 className="text-xl font-semibold mb-6 pb-2 border-b border-border">{t('settings.general')}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium mb-1 text-foreground">{t('settings.supportEmail')}</label>
              <input
                type="email"
                placeholder="support@store.com"
                className="w-full px-4 py-2 border border-input rounded-lg bg-background focus:ring-2 focus:ring-ring"
                value={formData.support_email}
                onChange={(e) => setFormData({ ...formData, support_email: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-foreground">{t('settings.currency')}</label>
              <select
                className="w-full px-4 py-2 border border-input rounded-lg bg-background focus:ring-2 focus:ring-ring"
                value={formData.currency}
                onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
              >
                <option value="ILS">ILS (₪)</option>
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
              </select>
            </div>
          </div>
        </section>

        <section className="bg-card p-6 rounded-xl shadow-sm border border-border">
          <h2 className="text-xl font-semibold mb-1 pb-2 border-b border-border">{t('settings.localization')}</h2>
          <p className="text-sm text-muted-foreground mt-3 mb-6">{t('settings.languagesHint')}</p>
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-3 text-foreground">{t('settings.supportedLanguages')}</label>
              <div className="flex flex-wrap gap-2 mb-4">
                {langs.map((code) => (
                  <span
                    key={code}
                    className="inline-flex items-center gap-2 rounded-full border border-border bg-muted/50 px-3 py-1.5 text-sm"
                  >
                    <span className="font-medium">{languageDisplayName(code, locale)}</span>
                    <span className="text-xs text-muted-foreground">{code}</span>
                    <button
                      type="button"
                      onClick={() => removeLanguage(code)}
                      className="text-muted-foreground hover:text-destructive transition-colors"
                      aria-label={`${t('common.delete')} ${code}`}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <label className="block text-sm font-medium mb-1 text-foreground">{t('settings.addLanguage')}</label>
              <div className="flex gap-2">
                <input
                  value={langQuery}
                  onChange={(e) => setLangQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      addLanguage(langQuery)
                    }
                  }}
                  placeholder={t('settings.addLanguagePlaceholder')}
                  className="flex-1 px-4 py-2 border border-input rounded-lg bg-background focus:ring-2 focus:ring-ring"
                />
                <button
                  type="button"
                  onClick={() => addLanguage(langQuery)}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 active:scale-[0.98] transition-all"
                >
                  {t('settings.add')}
                </button>
              </div>
              {languageSuggestions.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {languageSuggestions.map((l) => (
                    <button
                      key={l.code}
                      type="button"
                      onClick={() => addLanguage(l.code)}
                      className="rounded-full border border-border px-3 py-1 text-xs hover:bg-muted transition-colors"
                    >
                      {languageDisplayName(l.code, locale)} <span className="text-muted-foreground">{l.code}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-1 text-foreground">{t('settings.defaultLanguage')}</label>
              <select
                className="w-full md:w-1/2 px-4 py-2 border border-input rounded-lg bg-background focus:ring-2 focus:ring-ring"
                value={formData.default_language}
                onChange={(e) => setFormData({ ...formData, default_language: e.target.value })}
              >
                {langs.map((code) => (
                  <option key={code} value={code}>
                    {languageDisplayName(code, locale)} ({code})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </section>

        <section className="bg-card p-6 rounded-xl shadow-sm border border-border">
          <h2 className="text-xl font-semibold mb-1 pb-2 border-b border-border">{t('settings.navbar')}</h2>
          <p className="text-sm text-muted-foreground mt-3 mb-6">{t('settings.navbarHint')}</p>
          <div className="space-y-3">
            {navItems.map((item, index) => (
              <div
                key={item.id}
                className="flex flex-col gap-3 rounded-xl border border-border p-4 md:flex-row md:items-center"
              >
                <label className="flex items-center gap-2 shrink-0">
                  <input
                    type="checkbox"
                    className="w-4 h-4 rounded border-input"
                    checked={item.enabled}
                    onChange={(e) => updateNavItem(index, { enabled: e.target.checked })}
                  />
                  <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {t(`settings.navKind${item.kind.charAt(0).toUpperCase()}${item.kind.slice(1)}`)}
                  </span>
                </label>
                <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {langs.map((lang) => (
                    <input
                      key={lang}
                      value={item.label?.[lang] ?? ''}
                      placeholder={`${t('settings.navLabel')} (${languageDisplayName(lang, locale)}) — ${resolveNavLabel({ ...item, label: {} }, lang)}`}
                      onChange={(e) =>
                        updateNavItem(index, { label: { ...(item.label || {}), [lang]: e.target.value } })
                      }
                      className="w-full px-3 py-2 border border-input rounded-lg bg-background text-sm focus:ring-2 focus:ring-ring"
                    />
                  ))}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button type="button" aria-label={t('settings.navMoveUp')} onClick={() => moveNavItem(index, -1)} className="p-1.5 rounded-md hover:bg-muted">
                    <ChevronUp className="h-4 w-4" />
                  </button>
                  <button type="button" aria-label={t('settings.navMoveDown')} onClick={() => moveNavItem(index, 1)} className="p-1.5 rounded-md hover:bg-muted">
                    <ChevronDown className="h-4 w-4" />
                  </button>
                  {item.kind === 'custom' && (
                    <button type="button" aria-label={t('common.delete')} onClick={() => removeNavItem(index)} className="p-1.5 rounded-md text-destructive hover:bg-destructive/10">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex flex-col sm:flex-row gap-2">
            <input
              value={customLabel}
              onChange={(e) => setCustomLabel(e.target.value)}
              placeholder={t('settings.navCustomLabel')}
              className="flex-1 px-3 py-2 border border-input rounded-lg bg-background text-sm"
            />
            <input
              value={customHref}
              onChange={(e) => setCustomHref(e.target.value)}
              placeholder={t('settings.navCustomHref')}
              className="flex-1 px-3 py-2 border border-input rounded-lg bg-background text-sm"
            />
            <button
              type="button"
              onClick={addCustomNav}
              className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg border border-border text-sm font-medium hover:bg-muted transition-colors"
            >
              <Plus className="h-4 w-4" />
              {t('settings.navAddCustom')}
            </button>
          </div>
        </section>

        <section className="bg-card p-6 rounded-xl shadow-sm border border-border">
          <h2 className="text-xl font-semibold mb-6 pb-2 border-b border-border">{t('settings.reviewsModeration')}</h2>
          <div className="space-y-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                className="w-5 h-5 text-primary rounded border-input"
                checked={formData.review_moderation_enabled}
                onChange={(e) => setFormData({ ...formData, review_moderation_enabled: e.target.checked })}
              />
              <div>
                <span className="block text-sm font-medium text-foreground">{t('settings.enableModeration')}</span>
                <span className="block text-sm text-muted-foreground">{t('settings.enableModerationHint')}</span>
              </div>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                className="w-5 h-5 text-primary rounded border-input"
                checked={formData.allow_unverified_reviews}
                onChange={(e) => setFormData({ ...formData, allow_unverified_reviews: e.target.checked })}
              />
              <div>
                <span className="block text-sm font-medium text-foreground">{t('settings.allowUnverified')}</span>
                <span className="block text-sm text-muted-foreground">{t('settings.allowUnverifiedHint')}</span>
              </div>
            </label>
          </div>
        </section>

        <section className="bg-card p-6 rounded-xl shadow-sm border border-border">
          <h2 className="text-xl font-semibold mb-6 pb-2 border-b border-border">{t('settings.advanced')}</h2>
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-1 text-foreground">{t('settings.templateKey')}</label>
              <input
                type="text"
                placeholder="default"
                className="w-full md:w-1/2 px-4 py-2 border border-input rounded-lg bg-background focus:ring-2 focus:ring-ring"
                value={formData.template_key}
                onChange={(e) => setFormData({ ...formData, template_key: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1 text-foreground">{t('settings.customCss')}</label>
              <textarea
                className="w-full h-32 px-4 py-2 border border-input rounded-lg bg-background focus:ring-2 focus:ring-ring font-mono text-sm"
                placeholder={t('settings.customCssPlaceholder')}
                value={formData.custom_css}
                onChange={(e) => setFormData({ ...formData, custom_css: e.target.value })}
              />
            </div>
          </div>
        </section>

        <div className="flex justify-end pt-4">
          <button
            type="submit"
            disabled={loading}
            className="px-8 py-3 bg-primary text-primary-foreground rounded-lg font-bold hover:bg-primary/90 focus:ring-4 focus:ring-ring/30 transition-colors disabled:opacity-50 active:scale-[0.98]"
          >
            {loading ? t('settings.saving') : t('settings.save')}
          </button>
        </div>
      </form>
    </div>
  )
}
