'use client'

import { languageDisplayName } from '@/lib/languages'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'

export function StorefrontLanguageSwitcher({
  className = '',
  testId = 'language-switcher',
  lang: langProp,
  setLang: setLangProp,
  supportedLanguages: langsProp,
}: {
  className?: string
  testId?: string
  lang?: string
  setLang?: (lang: string) => void
  supportedLanguages?: string[]
}) {
  const ctx = useStorefrontTheme()
  const lang = langProp ?? ctx.lang
  const setLang = setLangProp ?? ctx.setLang
  const supportedLanguages = langsProp ?? ctx.supportedLanguages
  const langs = (() => {
    if (supportedLanguages.length >= 2) return supportedLanguages
    return Array.from(new Set([...supportedLanguages, lang, 'he', 'en'].filter(Boolean)))
  })()

  if (langs.length < 2) return null

  return (
    <select
      data-testid={testId}
      aria-label="Language"
      value={langs.includes(lang) ? lang : langs[0]}
      onChange={(e) => setLang(e.target.value)}
      className={`pointer-events-auto cursor-pointer bg-transparent text-sm font-medium outline-none ${className}`}
    >
      {langs.map((code) => (
        <option key={code} value={code}>
          {languageDisplayName(code, lang)}
        </option>
      ))}
    </select>
  )
}
