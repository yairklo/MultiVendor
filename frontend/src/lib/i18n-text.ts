/**
 * Resolves an i18n JSON field (e.g. product name/description stored as
 * {"en": "...", "he": "..."}) to a single display string for the given
 * language, falling back to Hebrew, then English, then whatever's there.
 */
export function resolveI18nText(value: unknown, lang: string = 'he'): string {
  if (value == null) return ''
  if (typeof value !== 'object') return String(value)
  const obj = value as Record<string, string>
  return obj[lang] || obj.he || obj.en || Object.values(obj)[0] || ''
}
