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
