'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { apiClient } from '@/lib/api/apiClient'
import { DEFAULT_STOREFRONT_THEME, resolveStorefrontTheme, StorefrontThemeClasses } from '@/lib/storefront-themes'

interface StorefrontThemeContextValue {
  theme: StorefrontThemeClasses
  templateKey: string | null
  logoUrl: string | null
}

const StorefrontThemeContext = createContext<StorefrontThemeContextValue | null>(null)

/**
 * Fetches the public /config once per tenant and resolves its template_key to a literal
 * Tailwind class bundle (lib/storefront-themes.ts) — every storefront page under
 * app/store/[tenant_slug]/layout.tsx reads this instead of each re-fetching /config itself.
 */
export function StorefrontThemeProvider({
  tenantSlug,
  children,
}: {
  tenantSlug: string
  children: React.ReactNode
}) {
  const [templateKey, setTemplateKey] = useState<string | null>(null)
  const [logoUrl, setLogoUrl] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    apiClient(`/api/v1/store/${tenantSlug}/config`)
      .then((data) => {
        if (cancelled) return
        setTemplateKey(data.template_key ?? null)
        setLogoUrl(data.logo_url ?? null)
      })
      .catch(() => {
        if (!cancelled) setTemplateKey(null)
      })
    return () => {
      cancelled = true
    }
  }, [tenantSlug])

  const value: StorefrontThemeContextValue = {
    theme: resolveStorefrontTheme(templateKey),
    templateKey,
    logoUrl,
  }

  return <StorefrontThemeContext.Provider value={value}>{children}</StorefrontThemeContext.Provider>
}

const NO_PROVIDER_FALLBACK: StorefrontThemeContextValue = {
  theme: DEFAULT_STOREFRONT_THEME,
  templateKey: null,
  logoUrl: null,
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
