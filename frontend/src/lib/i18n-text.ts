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

/** Cart line name for the current language; falls back to the API's single-language `product_name`. */
export function cartItemName(
  item: { product_name: string; product_name_i18n?: Record<string, string> | null },
  lang: string = 'he'
): string {
  return item.product_name_i18n ? resolveI18nText(item.product_name_i18n, lang) || item.product_name : item.product_name
}
