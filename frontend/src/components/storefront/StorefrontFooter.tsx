'use client'

import Link from 'next/link'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'
import { resolveImageUrl } from '@/lib/media'
import { resolveNavHref, resolveNavLabel, visibleNavItems } from '@/lib/storefront-nav'
import { he as heDict } from '@/lib/ui-i18n/he'
import { en as enDict } from '@/lib/ui-i18n/en'
import { translate } from '@/lib/ui-i18n/translate'

function chromeT(lang: string) {
  const dict = lang === 'he' || lang.startsWith('he') ? heDict : enDict
  return (key: string, vars?: Record<string, string | number>) => translate(dict, key, vars)
}

export function StorefrontFooter({ tenantSlug, storeName }: { tenantSlug: string; storeName: string }) {
  const { theme, lang, logoUrl, navItems } = useStorefrontTheme()
  const year = new Date().getFullYear()
  const items = visibleNavItems(navItems)
  const t = chromeT(lang)
  const shopHeading = t('storefront.shop')
  const supportHeading = t('storefront.support')
  const tagline = t('storefront.footerTagline')
  const myOrders = t('storefront.myOrders')
  const getInTouch = t('storefront.getInTouch')
  const rights = t('storefront.rights')

  return (
    <footer className={`mt-auto ${theme.footerClass}`}>
      <div className={`mx-auto grid max-w-6xl gap-8 px-4 py-10 md:grid-cols-3 md:px-8 ${theme.footerText}`}>
        <div>
          <h3 className={`mb-2 flex items-center gap-2 text-lg font-bold ${theme.headingFont}`}>
            {logoUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={resolveImageUrl(logoUrl)} alt="" className="h-8 w-auto max-w-[120px] object-contain" />
            ) : null}
            {storeName}
          </h3>
          <p className="text-sm opacity-80">{tagline}</p>
        </div>
        <div>
          <h4 className="mb-2 text-sm font-semibold uppercase tracking-wide opacity-70">{shopHeading}</h4>
          <ul className="space-y-1 text-sm">
            {items.map((item) => (
              <li key={item.id}>
                <Link href={resolveNavHref(tenantSlug, item)} className="transition-opacity hover:opacity-80 hover:underline">
                  {resolveNavLabel(item, lang)}
                </Link>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4 className="mb-2 text-sm font-semibold uppercase tracking-wide opacity-70">{supportHeading}</h4>
          <ul className="space-y-1 text-sm">
            <li><Link href="/account/orders" className="transition-opacity hover:opacity-80 hover:underline">{myOrders}</Link></li>
            <li><Link href={`/store/${tenantSlug}/pages/contact`} className="transition-opacity hover:opacity-80 hover:underline">{getInTouch}</Link></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-current/10 px-4 py-4 text-center text-xs opacity-60">
        &copy; {year} {storeName}. {rights}
      </div>
    </footer>
  )
}
