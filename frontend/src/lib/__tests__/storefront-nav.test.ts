import { describe, it, expect } from 'vitest'
import { resolvePageKeyHref } from '../storefront-nav'

describe('resolvePageKeyHref', () => {
  it('routes "home" to the store root, not a CMS page', () => {
    expect(resolvePageKeyHref('acme', 'home')).toBe('/store/acme')
  })

  it('routes "shop" to the dedicated catalog route, not a CMS page', () => {
    expect(resolvePageKeyHref('acme', 'shop')).toBe('/store/acme/shop')
  })

  it('routes any other page_key to the generic static-page route', () => {
    expect(resolvePageKeyHref('acme', 'about')).toBe('/store/acme/pages/about')
    expect(resolvePageKeyHref('acme', 'contact')).toBe('/store/acme/pages/contact')
    expect(resolvePageKeyHref('acme', 'faq')).toBe('/store/acme/pages/faq')
  })
})
