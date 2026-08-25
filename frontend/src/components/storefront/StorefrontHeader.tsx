'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Menu, ShoppingBag, X } from 'lucide-react'
import { useCart } from '@/context/CartContext'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'
import { resolveImageUrl } from '@/lib/media'
import { resolveNavHref, resolveNavLabel, visibleNavItems } from '@/lib/storefront-nav'
import { he as heDict } from '@/lib/ui-i18n/he'
import { en as enDict } from '@/lib/ui-i18n/en'
import { translate } from '@/lib/ui-i18n/translate'
import { StorefrontLanguageSwitcher } from './StorefrontLanguageSwitcher'

function chromeT(lang: string) {
  const dict = lang === 'he' || lang.startsWith('he') ? heDict : enDict
  return (key: string, vars?: Record<string, string | number>) => translate(dict, key, vars)
}

export function StorefrontHeader({
  tenantSlug,
  storeName,
  isLoggedIn,
}: {
  tenantSlug: string
  storeName: string
  /** Resolved server-side from the token cookie — reading it client-side here would
   * mismatch between the server-rendered HTML (no cookie access) and the client's
   * first render, breaking hydration. */
  isLoggedIn: boolean
}) {
  const { theme, lang, setLang, logoUrl, navItems, supportedLanguages } = useStorefrontTheme()
  const { cart, openDrawer } = useCart()
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)
  const cartCount = cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0
  const t = chromeT(lang)
  const items = visibleNavItems(navItems)

  const isActive = (href: string) => {
    if (href === `/store/${tenantSlug}`) return pathname === href
    if (href === '/marketplace') return pathname === href || pathname?.startsWith('/marketplace')
    return pathname?.startsWith(href)
  }

  return (
    <header className={`sticky top-0 z-40 ${theme.headerClass}`}>
      <div className={`mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 md:px-8 ${theme.headerText}`}>
        <Link href={`/store/${tenantSlug}`} className={`flex items-center gap-2.5 text-xl font-bold transition-opacity hover:opacity-80 ${theme.headingFont}`}>
          {logoUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={resolveImageUrl(logoUrl)}
              alt={storeName}
              className="h-9 w-auto max-h-9 max-w-[160px] object-contain"
            />
          ) : null}
          <span className={logoUrl ? 'hidden sm:inline' : undefined}>{storeName}</span>
        </Link>

        <nav className="hidden items-center gap-6 md:flex">
          {items.map((item) => {
            const href = resolveNavHref(tenantSlug, item)
            return (
              <Link
                key={item.id}
                href={href}
                className={`text-sm transition-colors ${isActive(href) ? theme.navLinkActiveClass : theme.navLinkClass}`}
              >
                {resolveNavLabel(item, lang)}
              </Link>
            )
          })}
        </nav>

        <div className="flex items-center gap-3">
          <StorefrontLanguageSwitcher
            testId="header-language-switcher"
            className={`hidden md:inline ${theme.navLinkClass}`}
            lang={lang}
            setLang={setLang}
            supportedLanguages={supportedLanguages}
          />
          <Link
            data-testid="account-link"
            href={isLoggedIn ? '/account/orders' : '/login'}
            className={`hidden text-sm md:inline ${theme.navLinkClass}`}
          >
            {isLoggedIn ? t('storefront.myOrders') : t('storefront.login')}
          </Link>
          <button
            type="button"
            data-testid="cart-icon"
            onClick={openDrawer}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold transition-colors duration-150 active:scale-[0.98] ${theme.primaryButtonClass}`}
          >
            <ShoppingBag className="h-4 w-4" />
            <span>{t('storefront.cart', { count: cartCount })}</span>
          </button>
          <button
            type="button"
            aria-label={t('storefront.toggleMenu')}
            className={`md:hidden transition-opacity hover:opacity-70 ${theme.headerText}`}
            onClick={() => setMobileOpen((v) => !v)}
          >
            {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <nav className={`flex flex-col gap-1 border-t border-current/10 px-4 py-3 md:hidden animate-in fade-in-0 slide-in-from-top-2 duration-200 ${theme.headerText}`}>
          {items.map((item) => {
            const href = resolveNavHref(tenantSlug, item)
            return (
              <Link
                key={item.id}
                href={href}
                onClick={() => setMobileOpen(false)}
                className={`rounded-lg px-2 py-2 text-sm ${isActive(href) ? theme.navLinkActiveClass : theme.navLinkClass}`}
              >
                {resolveNavLabel(item, lang)}
              </Link>
            )
          })}
          <div className={`rounded-lg px-2 py-2 ${theme.navLinkClass}`}>
            <StorefrontLanguageSwitcher className="w-full" lang={lang} setLang={setLang} supportedLanguages={supportedLanguages} />
          </div>
          <Link
            href={isLoggedIn ? '/account/orders' : '/login'}
            onClick={() => setMobileOpen(false)}
            className={`rounded-lg px-2 py-2 text-sm ${theme.navLinkClass}`}
          >
            {isLoggedIn ? t('storefront.myOrders') : t('storefront.login')}
          </Link>
        </nav>
      )}
    </header>
  )
}
