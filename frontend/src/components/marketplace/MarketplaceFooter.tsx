'use client'

import Link from 'next/link'
import { Store } from 'lucide-react'
import { useUiLocale } from '@/context/UiLocaleContext'

/** Cross-vendor equivalent of storefront/StorefrontFooter, styled with the platform's own
 * brand tokens (marketplace has no single tenant theme to read colors from). */
export function MarketplaceFooter() {
  const { t } = useUiLocale()
  const year = new Date().getFullYear()

  return (
    <footer className="mt-auto border-t border-border bg-secondary/40">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 text-foreground md:grid-cols-3 md:px-8">
        <div>
          <h3 className="mb-2 flex items-center gap-2 text-lg font-bold font-heading">
            <Store className="h-5 w-5 text-primary" />
            {t('marketplace.brand')}
          </h3>
          <p className="text-sm text-muted-foreground">
            {t('marketplace.subtitle')}
          </p>
        </div>
        <div>
          <h4 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">{t('marketplace.footerShop')}</h4>
          <ul className="space-y-1 text-sm">
            <li>
              <Link href="/marketplace" className="text-foreground/80 transition-colors hover:text-primary">
                {t('marketplace.browseMarketplace')}
              </Link>
            </li>
            <li>
              <Link href="/marketplace/checkout" className="text-foreground/80 transition-colors hover:text-primary">
                {t('marketplace.checkoutLink')}
              </Link>
            </li>
          </ul>
        </div>
        <div>
          <h4 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">{t('marketplace.footerSupport')}</h4>
          <ul className="space-y-1 text-sm">
            <li>
              <Link href="/account/orders" className="text-foreground/80 transition-colors hover:text-primary">
                {t('storefront.myOrders')}
              </Link>
            </li>
            <li>
              <Link href="/login" className="text-foreground/80 transition-colors hover:text-primary">
                {t('common.login')}
              </Link>
            </li>
          </ul>
        </div>
      </div>
      <div className="border-t border-border px-4 py-4 text-center text-xs text-muted-foreground">
        &copy; {year} {t('marketplace.brand')}. {t('marketplace.rights')}
      </div>
    </footer>
  )
}
