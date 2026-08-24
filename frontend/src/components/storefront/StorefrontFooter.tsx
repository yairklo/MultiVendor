'use client'

import Link from 'next/link'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'

export function StorefrontFooter({ tenantSlug, storeName }: { tenantSlug: string; storeName: string }) {
  const { theme } = useStorefrontTheme()
  const year = new Date().getFullYear()

  return (
    <footer className={`mt-auto ${theme.footerClass}`}>
      <div className={`mx-auto grid max-w-6xl gap-8 px-4 py-10 md:grid-cols-3 md:px-8 ${theme.footerText}`}>
        <div>
          <h3 className={`mb-2 text-lg font-bold ${theme.headingFont}`}>{storeName}</h3>
          <p className="text-sm opacity-80">Thoughtfully made, honestly priced.</p>
        </div>
        <div>
          <h4 className="mb-2 text-sm font-semibold uppercase tracking-wide opacity-70">Shop</h4>
          <ul className="space-y-1 text-sm">
            <li><Link href={`/store/${tenantSlug}`} className="transition-opacity hover:opacity-80 hover:underline">Home</Link></li>
            <li><Link href={`/store/${tenantSlug}/shop`} className="transition-opacity hover:opacity-80 hover:underline">Shop</Link></li>
            <li><Link href={`/store/${tenantSlug}/pages/about`} className="transition-opacity hover:opacity-80 hover:underline">About</Link></li>
            <li><Link href={`/store/${tenantSlug}/pages/contact`} className="transition-opacity hover:opacity-80 hover:underline">Contact</Link></li>
          </ul>
        </div>
        <div>
          <h4 className="mb-2 text-sm font-semibold uppercase tracking-wide opacity-70">Support</h4>
          <ul className="space-y-1 text-sm">
            <li><Link href="/account/orders" className="transition-opacity hover:opacity-80 hover:underline">My Orders</Link></li>
            <li><Link href={`/store/${tenantSlug}/pages/contact`} className="transition-opacity hover:opacity-80 hover:underline">Get in touch</Link></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-current/10 px-4 py-4 text-center text-xs opacity-60">
        &copy; {year} {storeName}. All rights reserved.
      </div>
    </footer>
  )
}
