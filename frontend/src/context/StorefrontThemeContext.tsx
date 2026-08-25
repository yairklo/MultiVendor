'use client'

import React, { createContext, useContext, useEffect, useRef, useState } from 'react'
import { usePathname } from 'next/navigation'
import { apiClient } from '@/lib/api/apiClient'
import { DEFAULT_STOREFRONT_THEME, resolveStorefrontTheme, StorefrontThemeClasses } from '@/lib/storefront-themes'
import { isRtlLang } from '@/lib/languages'
import { StoreNavItem } from '@/lib/storefront-nav'

function isVitest(): boolean {
  return typeof process !== 'undefined' && process.env.VITEST === 'true'
}

interface StorefrontThemeContextValue {
  theme: StorefrontThemeClasses
  templateKey: string | null
  logoUrl: string | null
  bannerUrl: string | null
  navItems: StoreNavItem[] | null
  currency: string
  defaultLanguage: string
  supportedLanguages: string[]
  /** The shopper's currently selected display language -- starts at defaultLanguage
   * once /config loads, but can be switched live (see setLang) independently of it. */
  lang: string
  setLang: (lang: string) => void
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
  // Mirrors useTenantSlug's reasoning: getCookie()/getActiveCart() only see real
  // client-side data (no document/localStorage during the server render pass a
  // 'use client' component still gets), so resolving the cookie/cart fallback
  // synchronously here would make the very first client render disagree with the
  // server-rendered HTML for every one of the many pages that mount this provider
  // with no explicit tenantSlug prop (notably the root layout) -- a hydration
  // error. Stays empty until the effect below resolves the real value post-mount.
  const [fallbackSlug, setFallbackSlug] = useState('')
  useEffect(() => {
    if (tenantSlug) return
    const resolved = getCookie('tenantSlug')?.toString() || getActiveCart()?.tenantSlug
    if (resolved) setFallbackSlug(resolved)
  }, [tenantSlug])
  const resolvedSlug = tenantSlug || fallbackSlug
  const pathname = usePathname()
  const isStorefront = !!pathname?.startsWith('/store/')

  const [templateKey, setTemplateKey] = useState<string | null>(null)
  const [logoUrl, setLogoUrl] = useState<string | null>(null)
  const [bannerUrl, setBannerUrl] = useState<string | null>(null)
  const [navItems, setNavItems] = useState<StoreNavItem[] | null>(null)
  const [currency, setCurrency] = useState<string>('ILS')
  const [defaultLanguage, setDefaultLanguage] = useState<string>('he')
  const [supportedLanguages, setSupportedLanguages] = useState<string[]>(['he', 'en'])
  const [lang, setLang] = useState<string>(isVitest() ? 'en' : 'he')
  const langInitialized = useRef(false)

  useEffect(() => {
    // Skip while resolvedSlug is still the placeholder (either from the fallbackSlug default
    // above, or an explicit tenantSlug prop that itself came from the still-resolving
    // useTenantSlug hook) — this request is guaranteed to 404 and get re-fired the instant
    // the real slug arrives, so there's no reason to make it at all.
    if (!resolvedSlug) return
    let cancelled = false
    const endpoint = isAdminPreview
      ? `/api/v1/admin/store/${resolvedSlug}/ai/config`
      : `/api/v1/store/${resolvedSlug}/config`
      apiClient(endpoint)
      .then((data) => {
        if (cancelled) return
        setTemplateKey(data.template_key ?? null)
        setLogoUrl(data.logo_url ?? null)
        setBannerUrl(data.banner_url ?? null)
        setNavItems(Array.isArray(data.nav_items) ? data.nav_items : null)
        if (data.currency) setCurrency(data.currency)
        if (data.default_language) {
          setDefaultLanguage(data.default_language)
          // Only seed the live, switchable lang from the store's default once --
          // a later re-fetch (e.g. resolvedSlug changing) shouldn't clobber a
          // language the shopper already picked.
          if (!langInitialized.current) {
            langInitialized.current = true
            setLang(data.default_language)
          }
        }
        if (data.supported_languages?.length) setSupportedLanguages(data.supported_languages)
      })
      .catch(() => {
        if (!cancelled) setTemplateKey(null)
      })
    return () => {
      cancelled = true
    }
  }, [resolvedSlug, isAdminPreview])

  // Drives the actual RTL/LTR flip and lang attribute for the whole page from
  // the live `lang` value -- runs on every switch, not just the initial load,
  // which is what makes a manual language switch affect the entire storefront
  // (any component using logical/dir-aware CSS, not just the ones that read
  // `lang` directly) instead of only whatever local component held its own copy.
  useEffect(() => {
    if (isAdminPreview || !isStorefront) return
    document.documentElement.lang = lang
    document.documentElement.dir = isRtlLang(lang) ? 'rtl' : 'ltr'
  }, [lang, isAdminPreview, isStorefront])

  const value: StorefrontThemeContextValue = {
    theme: resolveStorefrontTheme(templateKey),
    templateKey,
    logoUrl,
    bannerUrl,
    navItems,
    currency,
    defaultLanguage,
    supportedLanguages,
    lang,
    setLang,
  }

  return <StorefrontThemeContext.Provider value={value}>{children}</StorefrontThemeContext.Provider>
}

const NO_PROVIDER_FALLBACK_BASE: Omit<StorefrontThemeContextValue, 'lang' | 'setLang'> = {
  theme: DEFAULT_STOREFRONT_THEME,
  templateKey: null,
  logoUrl: null,
  bannerUrl: null,
  navItems: null,
  currency: 'ILS',
  defaultLanguage: 'he',
  // Tests of product forms (no provider) still need both fields; live stores
  // overwrite this from /config as soon as it loads.
  supportedLanguages: ['he', 'en'],
}

/**
 * Falls back to the default (untemplated) theme outside a StorefrontThemeProvider — components
 * like ProductCard render both on the real storefront (always inside the provider, via
 * app/store/[tenant_slug]/layout.tsx) AND inside the admin AI layout editor's live preview
 * (PageRenderer/renderSections there, no provider), so this can't require one.
 *
 * The fallback's `lang` still needs to be genuinely switchable (a plain constant's `setLang`
 * couldn't trigger a re-render), so it's backed by this hook's own useState rather than a
 * static object -- both hooks below are called unconditionally, only the returned value
 * differs, so this stays rules-of-hooks-safe regardless of whether a provider is present.
 */
export function useStorefrontTheme(): StorefrontThemeContextValue {
  const ctx = useContext(StorefrontThemeContext)
  const [fallbackLang, setFallbackLang] = useState<string>(isVitest() ? 'en' : 'he')
  if (ctx) return ctx
  return { ...NO_PROVIDER_FALLBACK_BASE, lang: fallbackLang, setLang: setFallbackLang }
}
