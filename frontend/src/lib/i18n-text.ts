/**
 * Resolves an i18n JSON field (e.g. product name/description stored as
 * {"en": "...", "he": "..."}) to a single display string for the given
 * language, falling back to English, then Hebrew, then whatever's there.
 * Existing storefront components each hand-roll this inline; this is the
 * shared version for new code (marketplace) rather than one more copy.
 */
export function resolveI18nText(value: unknown, lang: 'en' | 'he' = 'en'): string {
  if (value == null) return ''
  if (typeof value !== 'object') return String(value)
  const obj = value as Record<string, string>
  return obj[lang] || obj.en || obj.he || Object.values(obj)[0] || ''
}
