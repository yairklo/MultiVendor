/** Languages sellers commonly start with — the picker also accepts any BCP-47 tag. */
export const SUGGESTED_LANGUAGES: { code: string }[] = [
  { code: 'he' },
  { code: 'en' },
  { code: 'ar' },
  { code: 'ru' },
  { code: 'fr' },
  { code: 'es' },
  { code: 'de' },
  { code: 'it' },
  { code: 'pt' },
  { code: 'tr' },
  { code: 'am' },
  { code: 'fa' },
  { code: 'yi' },
  { code: 'uk' },
  { code: 'pl' },
  { code: 'nl' },
  { code: 'ro' },
  { code: 'hu' },
  { code: 'cs' },
  { code: 'el' },
  { code: 'sv' },
  { code: 'da' },
  { code: 'fi' },
  { code: 'no' },
  { code: 'ja' },
  { code: 'ko' },
  { code: 'zh' },
  { code: 'hi' },
  { code: 'th' },
  { code: 'vi' },
  { code: 'id' },
  { code: 'ms' },
  { code: 'bn' },
  { code: 'ur' },
]

const RTL_BASES = new Set(['he', 'ar', 'fa', 'ur', 'yi', 'ps', 'ckb', 'dv'])

export const LANG_CODE_RE = /^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,3}$/

export function normalizeLangCode(raw: string): string {
  return raw.trim().replace(/_/g, '-')
}

export function isValidLangCode(code: string): boolean {
  return LANG_CODE_RE.test(code)
}

export function languageBase(code: string): string {
  return code.split('-')[0]?.toLowerCase() || code
}

export function isRtlLang(code: string): boolean {
  return RTL_BASES.has(languageBase(code))
}

export function languageDisplayName(code: string, uiLocale: string = 'he'): string {
  try {
    const name = new Intl.DisplayNames([uiLocale, 'en'], { type: 'language' }).of(code)
    return name || code
  } catch {
    return code
  }
}

/** Storefront languages besides the built-in English/Hebrew form fields. */
export function extraLanguageCodes(supported: string[]): string[] {
  return supported.filter((l) => l !== 'en' && l !== 'he')
}

export function pickExtraLangValues(record: unknown): Record<string, string> {
  if (!record || typeof record !== 'object' || Array.isArray(record)) return {}
  const out: Record<string, string> = {}
  for (const [k, v] of Object.entries(record as Record<string, unknown>)) {
    if (k === 'en' || k === 'he') continue
    if (typeof v === 'string') out[k] = v
  }
  return out
}
