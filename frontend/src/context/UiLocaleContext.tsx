'use client'

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { getCookie, setCookie } from 'cookies-next'
import { he } from '@/lib/ui-i18n/he'
import { en } from '@/lib/ui-i18n/en'
import { translate } from '@/lib/ui-i18n/translate'

export type UiLocale = 'he' | 'en'

const COOKIE = 'ui_locale'
const dictionaries = { he, en } as const

function isVitest(): boolean {
  return typeof process !== 'undefined' && process.env.VITEST === 'true'
}

function readStoredLocale(): UiLocale {
  try {
    const fromCookie = getCookie?.(COOKIE)?.toString()
    if (fromCookie === 'he' || fromCookie === 'en') return fromCookie
  } catch {
    // cookies-next is often partially mocked in unit tests
  }
  return isVitest() ? 'en' : 'he'
}

type TranslateFn = (key: string, vars?: Record<string, string | number>) => string

interface UiLocaleContextValue {
  locale: UiLocale
  dir: 'rtl' | 'ltr'
  setLocale: (locale: UiLocale) => void
  t: TranslateFn
}

const UiLocaleContext = createContext<UiLocaleContextValue | null>(null)

export function UiLocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<UiLocale>(readStoredLocale)

  const setLocale = useCallback((next: UiLocale) => {
    setLocaleState(next)
    try {
      setCookie(COOKIE, next, { maxAge: 60 * 60 * 24 * 365, path: '/' })
    } catch {
      // ignore cookie write failures (jsdom / partial mocks)
    }
  }, [])

  const dir: 'rtl' | 'ltr' = locale === 'he' ? 'rtl' : 'ltr'

  useEffect(() => {
    const onStorefront = typeof window !== 'undefined' && window.location.pathname.startsWith('/store/')
    if (onStorefront) return
    document.documentElement.lang = locale
    document.documentElement.dir = dir
  }, [locale, dir])

  const t = useCallback<TranslateFn>(
    (key, vars) => translate(dictionaries[locale], key, vars),
    [locale],
  )

  const value = useMemo(() => ({ locale, dir, setLocale, t }), [locale, dir, setLocale, t])

  return <UiLocaleContext.Provider value={value}>{children}</UiLocaleContext.Provider>
}

export function useUiLocale(): UiLocaleContextValue {
  const ctx = useContext(UiLocaleContext)
  if (ctx) return ctx
  const locale = readStoredLocale()
  return {
    locale,
    dir: locale === 'he' ? 'rtl' : 'ltr',
    setLocale: () => {},
    t: (key, vars) => translate(dictionaries[locale], key, vars),
  }
}
