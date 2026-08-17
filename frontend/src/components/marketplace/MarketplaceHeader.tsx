'use client'

import Link from 'next/link'
import { ShoppingBag } from 'lucide-react'
import { useMarketplaceCart } from '@/context/MarketplaceCartContext'

export function MarketplaceHeader() {
  const { cart, openDrawer } = useMarketplaceCart()
  const cartCount = cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0

  return (
    <header className="sticky top-0 z-40 border-b border-gray-100 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 md:px-8">
        <Link href="/marketplace" className="text-xl font-bold text-gray-900">
          MultiVendor Marketplace
        </Link>
        <button
          type="button"
          data-testid="marketplace-cart-icon"
          onClick={openDrawer}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700"
        >
          <ShoppingBag className="h-4 w-4" />
          <span>Cart ({cartCount})</span>
        </button>
      </div>
    </header>
  )
}
