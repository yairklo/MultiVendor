'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import { useCart } from '@/context/CartContext'
import { useCurrency } from '@/hooks/useCurrency'
import { resolveImageUrl } from '@/lib/media'
import { useUiLocale } from '@/context/UiLocaleContext'

export function CartDrawer() {
  const { cart, isOpen, closeDrawer, incrementItem, decrementItem, removeItem } = useCart()
  const { formatCurrency } = useCurrency()
  const { t } = useUiLocale()
  const router = useRouter()

  if (!isOpen) return null

  const handleCheckout = () => {
    closeDrawer()
    router.push('/checkout')
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/40 animate-in fade-in-0 duration-200" onClick={closeDrawer} />
      <div
        data-testid="cart-drawer"
        className="relative flex h-full w-full max-w-md flex-col bg-card shadow-xl animate-in slide-in-from-right duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]"
      >
        <div className="flex items-center justify-between border-b border-border p-4">
          <h2 className="text-xl font-bold text-foreground">{t('cart.title')}</h2>
          <button
            aria-label={t('cart.close')}
            onClick={closeDrawer}
            className="text-2xl leading-none text-muted-foreground transition-colors hover:text-foreground"
          >
            &times;
          </button>
        </div>

        <div className="flex-1 overflow-auto p-4 space-y-4">
          {(!cart || cart.items.length === 0) && (
            <p className="text-center py-8 text-muted-foreground">{t('cart.empty')}</p>
          )}
          {cart?.items.map(item => (
            <div key={item.id} data-testid="cart-item" className="flex gap-3 border-b border-border pb-4">
              {item.image_url ? (
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
                    className="w-7 h-7 border border-border rounded-lg text-foreground transition-colors hover:bg-muted"
                  >
                    &minus;
                  </button>
                  <span className="w-6 text-center">{item.quantity}</span>
                  <button
                    aria-label={t('cart.increase')}
                    onClick={() => incrementItem(item.id)}
                    className="w-7 h-7 border border-border rounded-lg text-foreground transition-colors hover:bg-muted"
                  >
                    +
                  </button>
                  <button
                    aria-label={t('cart.remove')}
                    onClick={() => removeItem(item.id)}
                    className="ml-auto text-sm font-medium text-destructive transition-colors hover:underline"
                  >
                    {t('cart.removeLabel')}
                  </button>
                </div>
              </div>
              <div className="font-semibold text-foreground">{formatCurrency(Number(item.total_price))}</div>
            </div>
          ))}
        </div>

        {cart && cart.items.length > 0 && (
          <div className="border-t border-border p-4 space-y-3">
            <div className="flex justify-between font-bold text-lg text-foreground">
              <span>{t('cart.subtotal')}</span>
              <span data-testid="cart-subtotal">{formatCurrency(Number(cart.subtotal))}</span>
            </div>
            <button
              onClick={handleCheckout}
              className="w-full rounded-xl bg-primary py-3 font-bold text-primary-foreground transition-colors duration-150 hover:bg-primary/90 active:scale-[0.98]"
            >
              {t('cart.checkout')}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
