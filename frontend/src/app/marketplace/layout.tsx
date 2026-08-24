import React from 'react'
import { MarketplaceCartProvider } from '@/context/MarketplaceCartContext'
import { MarketplaceHeader } from '@/components/marketplace/MarketplaceHeader'
import { MarketplaceFooter } from '@/components/marketplace/MarketplaceFooter'
import { MarketplaceCartDrawer } from '@/components/marketplace/MarketplaceCartDrawer'

// The single-store cart (CartProvider/CartDrawer) is already global via the
// root layout, but it's a different resource entirely -- this scopes the
// marketplace cart's provider/drawer/header to just /marketplace/* so the
// two never get confused with each other.
export default function MarketplaceLayout({ children }: { children: React.ReactNode }) {
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
