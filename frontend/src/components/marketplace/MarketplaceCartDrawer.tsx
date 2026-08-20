'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import { Store } from 'lucide-react'
import { useMarketplaceCart } from '@/context/MarketplaceCartContext'
import { useCurrency } from '@/hooks/useCurrency'
import { MarketplaceCartItem } from '@/lib/marketplace-cart'

/** Cross-vendor equivalent of cart/CartDrawer, grouped by vendor so it's visually
 * obvious up front that checkout will split into one order per store. */
export function MarketplaceCartDrawer() {
  const { cart, isOpen, closeDrawer, incrementItem, decrementItem, removeItem } = useMarketplaceCart()
  const { formatCurrency } = useCurrency()
  const router = useRouter()

  if (!isOpen) return null

  const handleCheckout = () => {
    closeDrawer()
    router.push('/marketplace/checkout')
  }

  const groups: { tenant_id: number; tenant_name: string; items: MarketplaceCartItem[] }[] = []
  for (const item of cart?.items ?? []) {
    let group = groups.find(g => g.tenant_id === item.tenant_id)
    if (!group) {
      group = { tenant_id: item.tenant_id, tenant_name: item.tenant_name, items: [] }
      groups.push(group)
    }
    group.items.push(item)
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/40" onClick={closeDrawer} />
      <div data-testid="marketplace-cart-drawer" className="relative w-full max-w-md h-full bg-white shadow-xl flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-bold text-gray-900">Your Marketplace Cart</h2>
          <button
            aria-label="Close cart"
            onClick={closeDrawer}
            className="text-gray-500 hover:text-gray-800 text-2xl leading-none"
          >
            &times;
          </button>
        </div>

        <div className="flex-1 overflow-auto p-4 space-y-6">
          {(!cart || cart.items.length === 0) && (
            <p className="text-gray-500 text-center py-8">Your cart is empty.</p>
          )}
          {groups.map(group => (
            <div key={group.tenant_id} data-testid="marketplace-cart-vendor-group">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-blue-700">
                <Store className="h-3.5 w-3.5" />
                {group.tenant_name}
                <span className="font-normal text-gray-400">&middot; separate order</span>
              </div>
              <div className="space-y-4">
                {group.items.map(item => (
                  <div key={item.id} data-testid="marketplace-cart-item" className="flex gap-3 border-b pb-4">
                    {item.image_url ? (
                      <img src={item.image_url} alt={item.product_name} className="w-16 h-16 object-cover rounded-lg flex-shrink-0" />
                    ) : (
                      <div
                        role="img"
                        aria-label={item.product_name}
                        className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center text-[10px] text-gray-400 flex-shrink-0"
                      >
                        No image
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-gray-900 truncate">{item.product_name}</div>
                      <div className="text-gray-500">{formatCurrency(Number(item.unit_price))}</div>
                      <div className="flex items-center gap-2 mt-2">
                        <button
                          aria-label="Decrease quantity"
                          onClick={() => decrementItem(item.id)}
                          className="w-7 h-7 border rounded-lg text-gray-700 hover:bg-gray-100"
                        >
                          &minus;
                        </button>
                        <span className="w-6 text-center">{item.quantity}</span>
                        <button
                          aria-label="Increase quantity"
                          onClick={() => incrementItem(item.id)}
                          className="w-7 h-7 border rounded-lg text-gray-700 hover:bg-gray-100"
                        >
                          +
                        </button>
                        <button
                          aria-label="Remove item"
                          onClick={() => removeItem(item.id)}
                          className="ml-auto text-red-600 text-sm font-medium hover:underline"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                    <div className="font-semibold text-gray-900">{formatCurrency(Number(item.total_price))}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {cart && cart.items.length > 0 && (
          <div className="p-4 border-t space-y-3">
            <div className="flex justify-between text-sm text-gray-500">
              <span>{cart.vendor_count} vendor{cart.vendor_count === 1 ? '' : 's'} &middot; will become {cart.vendor_count} separate order{cart.vendor_count === 1 ? '' : 's'}</span>
            </div>
            <div className="flex justify-between font-bold text-lg text-gray-900">
              <span>Subtotal</span>
              <span data-testid="marketplace-cart-subtotal">{formatCurrency(Number(cart.subtotal))}</span>
            </div>
            <button
              onClick={handleCheckout}
              className="w-full bg-blue-600 text-white py-3 rounded-xl font-bold hover:bg-blue-700 transition-colors"
            >
              Proceed to Checkout
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
