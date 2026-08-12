'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Menu, ShoppingBag, X } from 'lucide-react'
import { useCart } from '@/context/CartContext'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'

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
  const { theme } = useStorefrontTheme()
  const { cart, openDrawer } = useCart()
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)
  const cartCount = cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0

  const navItems = [
    { label: 'Home', href: `/store/${tenantSlug}` },
    { label: 'Shop', href: `/store/${tenantSlug}/shop` },
    { label: 'About', href: `/store/${tenantSlug}/pages/about` },
    { label: 'Contact', href: `/store/${tenantSlug}/pages/contact` },
  ]

  const isActive = (href: string) => (href === `/store/${tenantSlug}` ? pathname === href : pathname?.startsWith(href))

  return (
    <header className={`sticky top-0 z-40 ${theme.headerClass}`}>
      <div className={`mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 md:px-8 ${theme.headerText}`}>
        <Link href={`/store/${tenantSlug}`} className={`text-xl font-bold ${theme.headingFont}`}>
          {storeName}
        </Link>

        <nav className="hidden items-center gap-6 md:flex">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`text-sm transition-colors ${isActive(item.href) ? theme.navLinkActiveClass : theme.navLinkClass}`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <Link
            data-testid="account-link"
            href={isLoggedIn ? '/account/orders' : '/login'}
            className={`hidden text-sm md:inline ${theme.navLinkClass}`}
          >
            {isLoggedIn ? 'My Orders' : 'Login'}
          </Link>
          <button
            type="button"
            data-testid="cart-icon"
            onClick={openDrawer}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold transition-colors ${theme.primaryButtonClass}`}
          >
            <ShoppingBag className="h-4 w-4" />
            <span>Cart ({cartCount})</span>
          </button>
          <button
            type="button"
            aria-label="Toggle menu"
            className={`md:hidden ${theme.headerText}`}
            onClick={() => setMobileOpen((v) => !v)}
          >
            {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <nav className={`flex flex-col gap-1 border-t border-current/10 px-4 py-3 md:hidden ${theme.headerText}`}>
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={`rounded-lg px-2 py-2 text-sm ${isActive(item.href) ? theme.navLinkActiveClass : theme.navLinkClass}`}
            >
              {item.label}
            </Link>
          ))}
          <Link
            href={isLoggedIn ? '/account/orders' : '/login'}
            onClick={() => setMobileOpen(false)}
            className={`rounded-lg px-2 py-2 text-sm ${theme.navLinkClass}`}
          >
            {isLoggedIn ? 'My Orders' : 'Login'}
          </Link>
        </nav>
      )}
    </header>
  )
}
