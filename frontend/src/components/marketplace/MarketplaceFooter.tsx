import Link from 'next/link'
import { Store } from 'lucide-react'

/** Cross-vendor equivalent of storefront/StorefrontFooter, styled with the platform's own
 * brand tokens (marketplace has no single tenant theme to read colors from). */
export function MarketplaceFooter() {
  const year = new Date().getFullYear()

  return (
    <footer className="mt-auto border-t border-border bg-secondary/40">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 text-foreground md:grid-cols-3 md:px-8">
        <div>
          <h3 className="mb-2 flex items-center gap-2 text-lg font-bold font-heading">
            <Store className="h-5 w-5 text-primary" />
            MultiVendor Marketplace
          </h3>
          <p className="text-sm text-muted-foreground">
            Products from every store on the platform, in one place.
          </p>
        </div>
        <div>
          <h4 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Shop</h4>
          <ul className="space-y-1 text-sm">
            <li>
              <Link href="/marketplace" className="text-foreground/80 transition-colors hover:text-primary">
                Browse Marketplace
              </Link>
            </li>
            <li>
              <Link href="/marketplace/checkout" className="text-foreground/80 transition-colors hover:text-primary">
                Checkout
              </Link>
            </li>
          </ul>
        </div>
        <div>
          <h4 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Support</h4>
          <ul className="space-y-1 text-sm">
            <li>
              <Link href="/account/orders" className="text-foreground/80 transition-colors hover:text-primary">
                My Orders
              </Link>
            </li>
            <li>
              <Link href="/login" className="text-foreground/80 transition-colors hover:text-primary">
                Login
              </Link>
            </li>
          </ul>
        </div>
      </div>
      <div className="border-t border-border px-4 py-4 text-center text-xs text-muted-foreground">
        &copy; {year} MultiVendor Marketplace. All rights reserved.
      </div>
    </footer>
  )
}
