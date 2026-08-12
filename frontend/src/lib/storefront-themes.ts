// Same "safelist" discipline as lib/design-tokens.ts and lib/product-card-styles.ts — Tailwind
// v4 scans source files for literal class-name tokens, so every value below MUST be a complete,
// statically-written string. template_key comes from the tenant's public /config response (a
// plain string the backend also validates against STOREFRONT_TEMPLATES), never rendered as CSS
// directly — it's only ever used as a lookup key into this map.
export type StorefrontThemeKey = 'aurora' | 'atelier' | 'nova'

export interface StorefrontThemeClasses {
  headingFont: string
  headerClass: string
  headerText: string
  footerClass: string
  footerText: string
  navLinkClass: string
  navLinkActiveClass: string
  primaryButtonClass: string
  outlineButtonClass: string
}

// The look untemplated stores keep today — unchanged so a tenant who never picks a template
// sees no visual difference from before this feature existed. Also the fallback used outside
// any StorefrontThemeProvider (e.g. the admin AI layout editor's preview pane).
export const DEFAULT_STOREFRONT_THEME: StorefrontThemeClasses = {
  headingFont: 'font-sans',
  headerClass: 'bg-white border-b border-gray-100',
  headerText: 'text-gray-900',
  footerClass: 'bg-white border-t border-gray-100',
  footerText: 'text-gray-500',
  navLinkClass: 'text-gray-600 hover:text-blue-600',
  navLinkActiveClass: 'text-blue-600 font-semibold',
  primaryButtonClass: 'bg-blue-600 text-white hover:bg-blue-700 rounded-lg',
  outlineButtonClass: 'border border-gray-300 text-gray-900 hover:bg-gray-50 rounded-lg',
}

export const STOREFRONT_THEMES: Record<StorefrontThemeKey, StorefrontThemeClasses> = {
  aurora: {
    headingFont: 'font-serif',
    headerClass: 'bg-[#faf8f5] border-b border-black/5',
    headerText: 'text-gray-900',
    footerClass: 'bg-[#f1ede7] border-t border-black/5',
    footerText: 'text-gray-600',
    navLinkClass: 'text-gray-600 hover:text-indigo-600',
    navLinkActiveClass: 'text-indigo-600 font-semibold',
    primaryButtonClass: 'bg-indigo-600 text-white hover:bg-indigo-700 rounded-full',
    outlineButtonClass: 'border border-gray-900 text-gray-900 hover:bg-gray-900 hover:text-white rounded-full',
  },
  atelier: {
    headingFont: 'font-serif',
    headerClass: 'bg-[#15130f] border-b border-white/10',
    headerText: 'text-[#f5f0e6]',
    footerClass: 'bg-[#0f0d0a] border-t border-white/10',
    footerText: 'text-[#f5f0e6]/60',
    navLinkClass: 'text-[#f5f0e6]/70 hover:text-[#c9a24b]',
    navLinkActiveClass: 'text-[#c9a24b] font-semibold',
    primaryButtonClass: 'bg-[#c9a24b] text-[#15130f] hover:bg-[#dab662] rounded-none',
    outlineButtonClass: 'border border-[#c9a24b] text-[#c9a24b] hover:bg-[#c9a24b] hover:text-[#15130f] rounded-none',
  },
  nova: {
    headingFont: 'font-sans',
    headerClass: 'bg-white border-b-2 border-gray-900',
    headerText: 'text-gray-900',
    footerClass: 'bg-gray-900',
    footerText: 'text-gray-300',
    navLinkClass: 'text-gray-700 hover:text-[#f0653a]',
    navLinkActiveClass: 'text-[#f0653a] font-bold',
    primaryButtonClass: 'bg-[#f0653a] text-white hover:bg-[#d9532b] rounded-lg',
    outlineButtonClass: 'border-2 border-gray-900 text-gray-900 hover:bg-gray-900 hover:text-white rounded-lg',
  },
}

export function resolveStorefrontTheme(templateKey: unknown): StorefrontThemeClasses {
  return typeof templateKey === 'string' && templateKey in STOREFRONT_THEMES
    ? STOREFRONT_THEMES[templateKey as StorefrontThemeKey]
    : DEFAULT_STOREFRONT_THEME
}
