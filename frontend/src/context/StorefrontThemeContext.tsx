'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { apiClient } from '@/lib/api/apiClient'
import { DEFAULT_STOREFRONT_THEME, resolveStorefrontTheme, StorefrontThemeClasses } from '@/lib/storefront-themes'

interface StorefrontThemeContextValue {
  theme: StorefrontThemeClasses
  templateKey: string | null
  logoUrl: string | null
  currency: string
  defaultLanguage: string
  supportedLanguages: string[]
}

const StorefrontThemeContext = createContext<StorefrontThemeContextValue | null>(null)

/**
 * Fetches the public /config once per tenant and resolves its template_key to a literal
 * Tailwind class bundle (lib/storefront-themes.ts) — every storefront page under
 * app/store/[tenant_slug]/layout.tsx reads this instead of each re-fetching /config itself.
 */
import { getActiveCart } from '@/lib/cart'
import { getCookie } from 'cookies-next'

export function StorefrontThemeProvider({
  tenantSlug,
  children,
  isAdminPreview = false,
}: {
  tenantSlug?: string
  children: React.ReactNode
  isAdminPreview?: boolean
}) {
  const resolvedSlug = tenantSlug || getCookie('tenantSlug')?.toString() || getActiveCart()?.tenantSlug || 'test-tenant'
  
  const [templateKey, setTemplateKey] = useState<string | null>(null)
  const [logoUrl, setLogoUrl] = useState<string | null>(null)
  const [currency, setCurrency] = useState<string>('ILS')
  const [defaultLanguage, setDefaultLanguage] = useState<string>('he')
  const [supportedLanguages, setSupportedLanguages] = useState<string[]>(['he'])

  useEffect(() => {
    let cancelled = false
    const endpoint = isAdminPreview
      ? `/api/v1/admin/store/${resolvedSlug}/ai/config`
      : `/api/v1/store/${resolvedSlug}/config`
      apiClient(endpoint)
      .then((data) => {
        if (cancelled) return
        setTemplateKey(data.template_key ?? null)
        setLogoUrl(data.logo_url ?? null)
        if (data.currency) setCurrency(data.currency)
        if (data.default_language) {
          setDefaultLanguage(data.default_language)
          if (!isAdminPreview) {
            document.documentElement.lang = data.default_language
            document.documentElement.dir = data.default_language === 'he' ? 'rtl' : 'ltr'
          }
        }
        if (data.supported_languages) setSupportedLanguages(data.supported_languages)
      })
      .catch(() => {
        if (!cancelled) setTemplateKey(null)
      })
    return () => {
      cancelled = true
    }
  }, [resolvedSlug, isAdminPreview])

  const value: StorefrontThemeContextValue = {
    theme: resolveStorefrontTheme(templateKey),
    templateKey,
    logoUrl,
    currency,
    defaultLanguage,
    supportedLanguages,
  }

  return <StorefrontThemeContext.Provider value={value}>{children}</StorefrontThemeContext.Provider>
}

const NO_PROVIDER_FALLBACK: StorefrontThemeContextValue = {
  theme: DEFAULT_STOREFRONT_THEME,
  templateKey: null,
  logoUrl: null,
  currency: 'ILS',
  defaultLanguage: 'he',
  supportedLanguages: ['he'],
}

/**
 * Falls back to the default (untemplated) theme outside a StorefrontThemeProvider — components
 * like ProductCard render both on the real storefront (always inside the provider, via
 * app/store/[tenant_slug]/layout.tsx) AND inside the admin AI layout editor's live preview
 * (PageRenderer/renderSections there, no provider), so this can't require one.
 */
export function useStorefrontTheme(): StorefrontThemeContextValue {
  const ctx = useContext(StorefrontThemeContext)
  return ctx ?? NO_PROVIDER_FALLBACK
}
