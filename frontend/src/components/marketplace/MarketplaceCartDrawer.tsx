'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import { Store } from 'lucide-react'
import { useMarketplaceCart } from '@/context/MarketplaceCartContext'
import { useCurrency } from '@/hooks/useCurrency'
import { MarketplaceCartItem } from '@/lib/marketplace-cart'
import { resolveImageUrl } from '@/lib/media'
import { useUiLocale } from '@/context/UiLocaleContext'

/** Cross-vendor equivalent of cart/CartDrawer, grouped by vendor so it's visually
 * obvious up front that checkout will split into one order per store. */
export function MarketplaceCartDrawer() {
  const { cart, isOpen, closeDrawer, incrementItem, decrementItem, removeItem, pendingItemIds } = useMarketplaceCart()
  const { formatCurrency } = useCurrency()
  const { t } = useUiLocale()
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
      <div className="absolute inset-0 bg-black/40 animate-in fade-in-0 duration-200" onClick={closeDrawer} />
      <div
        data-testid="marketplace-cart-drawer"
        className="relative flex h-full w-full max-w-md flex-col bg-card shadow-xl animate-in slide-in-from-right duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]"
      >
        <div className="flex items-center justify-between border-b border-border p-4">
          <h2 className="text-xl font-bold text-foreground">{t('marketplace.cartTitle')}</h2>
          <button
            aria-label={t('marketplace.closeCart')}
            onClick={closeDrawer}
            className="text-2xl leading-none text-muted-foreground transition-colors hover:text-foreground"
          >
            &times;
          </button>
        </div>

        <div className="flex-1 overflow-auto p-4 space-y-6">
          {(!cart || cart.items.length === 0) && (
            <p className="text-center py-8 text-muted-foreground">{t('marketplace.emptyCart')}</p>
          )}
          {groups.map(group => (
            <div key={group.tenant_id} data-testid="marketplace-cart-vendor-group">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-primary">
                <Store className="h-3.5 w-3.5" />
                {group.tenant_name}
                <span className="font-normal text-muted-foreground">&middot; {t('marketplace.separateOrder')}</span>
              </div>
              <div className="space-y-4">
                {group.items.map(item => (
                  <div key={item.id} data-testid="marketplace-cart-item" className="flex gap-3 border-b border-border pb-4">
                    {item.image_url ? (
                      // Arbitrary vendor-supplied URLs with no host allowlist, same
                      // reasoning as storefront/ProductCard.
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={resolveImageUrl(item.image_url)} alt={item.product_name} className="w-16 h-16 object-cover rounded-lg flex-shrink-0" />
                    ) : (
                      <div
                        role="img"
                        aria-label={item.product_name}
                        className="w-16 h-16 bg-muted rounded-lg flex items-center justify-center text-[10px] text-muted-foreground flex-shrink-0"
                      >
                        {t('common.noImage')}
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-foreground truncate">{item.product_name}</div>
                      <div className="text-muted-foreground">{formatCurrency(Number(item.unit_price))}</div>
                      <div className="flex items-center gap-2 mt-2">
                        <button
                          aria-label={t('cart.decrease')}
                          onClick={() => decrementItem(item.id)}
                          disabled={pendingItemIds.has(item.id)}
                          className="w-7 h-7 border border-border rounded-lg text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          &minus;
                        </button>
                        <span className="w-6 text-center">{item.quantity}</span>
                        <button
                          aria-label={t('cart.increase')}
                          onClick={() => incrementItem(item.id)}
                          disabled={pendingItemIds.has(item.id)}
                          className="w-7 h-7 border border-border rounded-lg text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          +
                        </button>
                        <button
                          aria-label={t('cart.remove')}
                          onClick={() => removeItem(item.id)}
                          disabled={pendingItemIds.has(item.id)}
                          className="ml-auto text-sm font-medium text-destructive transition-colors hover:underline disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {t('cart.removeLabel')}
                        </button>
                      </div>
                    </div>
                    <div className="font-semibold text-foreground">{formatCurrency(Number(item.total_price))}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {cart && cart.items.length > 0 && (
          <div className="border-t border-border p-4 space-y-3">
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>{cart.vendor_count === 1 ? t('marketplace.vendorSplit', { count: cart.vendor_count }) : t('marketplace.vendorSplitPlural', { count: cart.vendor_count })}</span>
            </div>
            <div className="flex justify-between font-bold text-lg text-foreground">
              <span>{t('marketplace.subtotal')}</span>
              <span data-testid="marketplace-cart-subtotal">{formatCurrency(Number(cart.subtotal))}</span>
            </div>
            <button
              onClick={handleCheckout}
              className="w-full rounded-xl bg-primary py-3 font-bold text-primary-foreground transition-colors duration-150 hover:bg-primary/90 active:scale-[0.98]"
            >
              {t('marketplace.checkout')}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
