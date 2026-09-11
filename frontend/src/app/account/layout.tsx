import React from 'react'
import { MarketplaceCartProvider } from '@/context/MarketplaceCartContext'
import { MarketplaceHeader } from '@/components/marketplace/MarketplaceHeader'
import { MarketplaceFooter } from '@/components/marketplace/MarketplaceFooter'
import { MarketplaceCartDrawer } from '@/components/marketplace/MarketplaceCartDrawer'

// /account/* (e.g. /account/orders) sits outside /store/[tenant_slug]/* and
// /marketplace/*, so it inherited only the bare root layout -- no header/nav
// at all, trapping the user with no way out except the browser back button.
// A customer's orders can span multiple stores, so the cross-store
// marketplace chrome (which already links to /account/orders) is the
// natural nav for this area, not a single store's storefront header.
export default function AccountLayout({ children }: { children: React.ReactNode }) {
  return (
    <MarketplaceCartProvider>
      <div className="flex min-h-screen flex-col">
        <MarketplaceHeader />
        <div className="flex-1">{children}</div>
        <MarketplaceFooter />
      </div>
      <MarketplaceCartDrawer />
    </MarketplaceCartProvider>
  )
}
