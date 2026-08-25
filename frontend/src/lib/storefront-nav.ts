import { resolveI18nText } from '@/lib/i18n-text'

export type NavKind = 'home' | 'shop' | 'marketplace' | 'page' | 'custom'

export interface StoreNavItem {
  id: string
  enabled: boolean
  kind: NavKind
  page_key?: string | null
  href?: string | null
  label?: Record<string, string>
}

export const DEFAULT_NAV_ITEMS: StoreNavItem[] = [
  { id: 'home', enabled: true, kind: 'home', label: {} },
  { id: 'shop', enabled: true, kind: 'shop', label: {} },
  { id: 'marketplace', enabled: true, kind: 'marketplace', label: {} },
  { id: 'about', enabled: true, kind: 'page', page_key: 'about', label: {} },
  { id: 'contact', enabled: true, kind: 'page', page_key: 'contact', label: {} },
]

const DEFAULT_LABELS: Record<string, Record<string, string>> = {
  home: { he: 'בית', en: 'Home' },
  shop: { he: 'חנות', en: 'Shop' },
  marketplace: { he: 'מרקטפלייס', en: 'Marketplace' },
  about: { he: 'אודות', en: 'About' },
  contact: { he: 'צור קשר', en: 'Contact' },
}

export function effectiveNavItems(items: StoreNavItem[] | null | undefined): StoreNavItem[] {
  if (!items || items.length === 0) return DEFAULT_NAV_ITEMS
  return items
}

export function visibleNavItems(items: StoreNavItem[] | null | undefined): StoreNavItem[] {
  return effectiveNavItems(items).filter((item) => item.enabled)
}

// Resolves an AI/template-authored button_group NAVIGATE actionPayload.page_key to a real
// storefront URL. Most page_keys are generic CMS pages (about/contact/...) served at
// /store/{slug}/pages/{key}, but 'home' and 'shop' are dedicated, code-driven routes rather than
// StorePage rows — special-cased here so a template's "Shop the collection" CTA (page_key:
// 'shop') actually lands on the catalog page instead of a nonexistent CMS page called "shop".
export function resolvePageKeyHref(tenantSlug: string, pageKey: string): string {
  if (pageKey === 'home') return `/store/${tenantSlug}`
  if (pageKey === 'shop') return `/store/${tenantSlug}/shop`
  return `/store/${tenantSlug}/pages/${pageKey}`
}

export function resolveNavHref(tenantSlug: string, item: StoreNavItem): string {
  switch (item.kind) {
    case 'home':
      return `/store/${tenantSlug}`
    case 'shop':
      return `/store/${tenantSlug}/shop`
    case 'marketplace':
      return '/marketplace'
    case 'page':
      return `/store/${tenantSlug}/pages/${item.page_key || item.id}`
    case 'custom':
      return item.href || '#'
  }
}

export function resolveNavLabel(item: StoreNavItem, lang: string): string {
  const fromItem = resolveI18nText(item.label, lang)
  if (fromItem) return fromItem
  const defaults = DEFAULT_LABELS[item.id] || (item.page_key ? DEFAULT_LABELS[item.page_key] : undefined)
  const fromDefault = defaults ? resolveI18nText(defaults, lang) : ''
  if (fromDefault) return fromDefault
  return item.page_key || item.id
}
