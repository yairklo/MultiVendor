'use client'

import { useState, useSyncExternalStore } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { getCookie } from 'cookies-next'
import { Menu, ShoppingBag, X } from 'lucide-react'
import { useMarketplaceCart } from '@/context/MarketplaceCartContext'
import { useUiLocale } from '@/context/UiLocaleContext'
import { UiLanguageSwitcher } from '@/components/ui/UiLanguageSwitcher'

// SSR/hydration-safe cookie read -- see hooks/useTenantSlug.ts for why a
// plain useEffect+useState pair isn't used here.
function subscribeNoop(): () => void {
  return () => {}
}
function getLoggedInSnapshot(): boolean {
  return !!getCookie('token')
}
function getLoggedInServerSnapshot(): boolean {
  return false
}

export function MarketplaceHeader() {
  const { cart, openDrawer } = useMarketplaceCart()
  const { t } = useUiLocale()
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)
  const isLoggedIn = useSyncExternalStore(subscribeNoop, getLoggedInSnapshot, getLoggedInServerSnapshot)
  const cartCount = cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0

  const isActive = (href: string) => (href === '/marketplace' ? pathname === href : pathname?.startsWith(href))

  const navLinkClass = (href: string) =>
    `text-[13px] tracking-[0.14em] uppercase transition-colors ${
      isActive(href) ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
    }`

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 md:px-8">
        <Link
          href="/marketplace"
          className="font-heading text-2xl font-medium text-foreground transition-opacity hover:opacity-70"
        >
          {t('marketplace.brand')}
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          <Link href="/marketplace" className={navLinkClass('/marketplace')}>
            {t('marketplace.browse')}
          </Link>
          <Link
            data-testid="account-link"
            href={isLoggedIn ? '/account/orders' : '/login'}
            className={navLinkClass(isLoggedIn ? '/account/orders' : '/login')}
          >
            {isLoggedIn ? t('storefront.myOrders') : t('common.login')}
          </Link>
          <UiLanguageSwitcher className="text-muted-foreground" />
        </nav>

        <div className="flex items-center gap-3">
          <button
            type="button"
            data-testid="marketplace-cart-icon"
            onClick={openDrawer}
            className="relative flex items-center gap-2 text-sm text-foreground transition-opacity hover:opacity-70 active:scale-[0.98] motion-safe:transition-transform"
          >
            <ShoppingBag className="h-5 w-5" strokeWidth={1.5} />
            <span className="sr-only">{t('marketplace.cart', { count: cartCount })}</span>
            <span className="tabular-nums text-[13px]">{cartCount}</span>
          </button>
          <button
            type="button"
            aria-label={t('storefront.toggleMenu')}
            className="text-foreground md:hidden"
            onClick={() => setMobileOpen((v) => !v)}
          >
            {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <nav className="flex flex-col gap-1 border-t border-border px-4 py-3 md:hidden motion-safe:animate-in motion-safe:fade-in-0 motion-safe:slide-in-from-top-2 motion-safe:duration-200">
          <Link
            href="/marketplace"
            onClick={() => setMobileOpen(false)}
            className={`rounded-sm px-2 py-2 ${navLinkClass('/marketplace')}`}
          >
            {t('marketplace.browse')}
          </Link>
          <Link
            href={isLoggedIn ? '/account/orders' : '/login'}
            onClick={() => setMobileOpen(false)}
            className={`rounded-sm px-2 py-2 ${navLinkClass(isLoggedIn ? '/account/orders' : '/login')}`}
          >
            {isLoggedIn ? t('storefront.myOrders') : t('common.login')}
          </Link>
          <div className="px-2 py-2">
            <UiLanguageSwitcher />
          </div>
        </nav>
      )}
    </header>
  )
}
