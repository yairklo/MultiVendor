'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { getCookie } from 'cookies-next'
import { Menu, ShoppingBag, Store, X } from 'lucide-react'
import { useMarketplaceCart } from '@/context/MarketplaceCartContext'
import { useUiLocale } from '@/context/UiLocaleContext'
import { UiLanguageSwitcher } from '@/components/ui/UiLanguageSwitcher'

export function MarketplaceHeader() {
  const { cart, openDrawer } = useMarketplaceCart()
  const { t } = useUiLocale()
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const cartCount = cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0

  useEffect(() => {
    setIsLoggedIn(!!getCookie('token'))
  }, [])

  const isActive = (href: string) => (href === '/marketplace' ? pathname === href : pathname?.startsWith(href))

  const navLinkClass = (href: string) =>
    `text-sm transition-colors ${
      isActive(href) ? 'font-semibold text-foreground' : 'text-muted-foreground hover:text-foreground'
    }`

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 md:px-8">
        <Link
          href="/marketplace"
          className="flex items-center gap-2 text-xl font-bold text-foreground font-heading transition-opacity hover:opacity-80"
        >
          <Store className="h-5 w-5 text-primary" />
          {t('marketplace.brand')}
        </Link>

        <nav className="hidden items-center gap-6 md:flex">
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
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors duration-150 hover:bg-primary/90 active:scale-[0.98]"
          >
            <ShoppingBag className="h-4 w-4" />
            <span>{t('marketplace.cart', { count: cartCount })}</span>
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
        <nav className="flex flex-col gap-1 border-t border-border px-4 py-3 md:hidden animate-in fade-in-0 slide-in-from-top-2 duration-200">
          <Link
            href="/marketplace"
            onClick={() => setMobileOpen(false)}
            className={`rounded-lg px-2 py-2 ${navLinkClass('/marketplace')}`}
          >
            {t('marketplace.browse')}
          </Link>
          <Link
            href={isLoggedIn ? '/account/orders' : '/login'}
            onClick={() => setMobileOpen(false)}
            className={`rounded-lg px-2 py-2 ${navLinkClass(isLoggedIn ? '/account/orders' : '/login')}`}
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
