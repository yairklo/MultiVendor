'use client'

import Link from 'next/link'
import { useUiLocale } from '@/context/UiLocaleContext'

/** Cross-vendor equivalent of storefront/StorefrontFooter, styled with the platform's own
 * brand tokens (marketplace has no single tenant theme to read colors from). */
export function MarketplaceFooter() {
  const { t } = useUiLocale()
  const year = new Date().getFullYear()

  return (
    <footer className="mt-auto border-t border-border">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-14 text-foreground md:grid-cols-[1.4fr_1fr_1fr] md:px-8">
        <div>
          <h3 className="mb-3 font-heading text-3xl font-medium leading-none">
            {t('marketplace.brand')}
          </h3>
          <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
            {t('marketplace.manifesto')}
          </p>
        </div>
        <div>
          <h4 className="mb-3 text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground">{t('marketplace.footerShop')}</h4>
          <ul className="space-y-2 text-sm">
            <li>
              <Link href="/marketplace" className="text-foreground/80 transition-colors hover:text-foreground">
                {t('marketplace.browseMarketplace')}
              </Link>
            </li>
            <li>
              <Link href="/marketplace/checkout" className="text-foreground/80 transition-colors hover:text-foreground">
                {t('marketplace.checkoutLink')}
              </Link>
            </li>
          </ul>
        </div>
        <div>
          <h4 className="mb-3 text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground">{t('marketplace.footerSupport')}</h4>
          <ul className="space-y-2 text-sm">
            <li>
              <Link href="/account/orders" className="text-foreground/80 transition-colors hover:text-foreground">
                {t('storefront.myOrders')}
              </Link>
            </li>
            <li>
              <Link href="/login" className="text-foreground/80 transition-colors hover:text-foreground">
                {t('common.login')}
              </Link>
            </li>
          </ul>
        </div>
      </div>
      <div className="border-t border-border px-4 py-4 text-center text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
        &copy; {year} {t('marketplace.brand')} · {t('marketplace.rights')}
      </div>
    </footer>
  )
}
