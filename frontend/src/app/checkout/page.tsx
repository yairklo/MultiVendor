'use client'

import React, { useState } from 'react'
import { apiClient } from '@/lib/api/apiClient'
import { getActiveCart } from '@/lib/cart'
import { useCart } from '@/context/CartContext'
import { useOrders } from '@/hooks/useOrders'
import { useToast } from '@/context/ToastContext'
import { useCurrency } from '@/hooks/useCurrency'
import { useRouter } from 'next/navigation'
import { StripeCardForm } from '@/components/checkout/StripeCardForm'
import { useUiLocale } from '@/context/UiLocaleContext'

export default function CheckoutPage() {
  const { t } = useUiLocale()
  const shippingOptions = [
    { id: 1, name: t('checkout.standardShipping'), price: 5 },
    { id: 2, name: t('checkout.expressShipping'), price: 15 }
  ]
  const { cart, loading, clear } = useCart()
  const { formatCurrency } = useCurrency()
  const { payOrder, cancelOrder, fetchOrder } = useOrders()
  const { showToast } = useToast()
  const [error, setError] = useState<string>('')
  const [submitting, setSubmitting] = useState(false)
  const [payingOrder, setPayingOrder] = useState<any>(null)
  const [paymentDone, setPaymentDone] = useState(false)
  const [payBusy, setPayBusy] = useState(false)
  const [stripePayment, setStripePayment] = useState<{ clientSecret: string; publishableKey: string } | null>(null)
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [address, setAddress] = useState('')
  const [couponInput, setCouponInput] = useState('')
  const [appliedCoupon, setAppliedCoupon] = useState<any>(null)
  const [applyingCoupon, setApplyingCoupon] = useState(false)
  const [shippingMethodId, setShippingMethodId] = useState<number>(1)
  const router = useRouter()

  const activeCart = getActiveCart()

  const subtotal = cart ? Number(cart.subtotal) : 0
  const discountAmount = appliedCoupon
    ? appliedCoupon.discount_type === 'percentage'
      ? subtotal * (Number(appliedCoupon.discount_val) / 100)
      : Math.min(Number(appliedCoupon.discount_val), subtotal)
    : 0
  
  const isDigitalOnly = !!cart && cart.items.length > 0 && cart.items.every(item => item.product_type !== 'physical')
  const requiresShippingAddress = !!cart && cart.items.length > 0 && !isDigitalOnly

  const selectedShipping = shippingOptions.find(o => o.id === shippingMethodId)
  const shippingCost = requiresShippingAddress ? (selectedShipping?.price || 0) : 0
  const total = Math.max(subtotal - discountAmount, 0) + shippingCost

  const handleApplyCoupon = async () => {
    if (!activeCart || !couponInput.trim()) return
    setApplyingCoupon(true)
    try {
      const coupon = await apiClient(
        `/api/v1/store/${activeCart.tenantSlug}/coupons/validate?coupon_code=${encodeURIComponent(couponInput.trim())}`,
        { method: 'POST' }
      )
      setAppliedCoupon(coupon)
      showToast(t('checkout.couponAppliedToast', { code: coupon.code }), 'success')
    } catch (e: any) {
      showToast(e.message || t('checkout.invalidCoupon'), 'error')
    } finally {
      setApplyingCoupon(false)
    }
  }

  const handleRemoveCoupon = () => {
    setAppliedCoupon(null)
    setCouponInput('')
  }


  const handleCheckout = async () => {
    if (!activeCart || !cart) return
    try {
      setError('')
      setSubmitting(true)

      const payload: Record<string, unknown> = {
        cart_id: activeCart.cartId,
        payment_token: crypto.randomUUID(),
      }

      if (requiresShippingAddress) {
        payload.shipping_address = {
          full_name: fullName,
          email,
          address_line_1: address,
        }
        payload.shipping_method_id = shippingMethodId
      }

      if (appliedCoupon) {
        payload.coupon_code = appliedCoupon.code
      }

      const order = await apiClient(`/api/v1/store/${activeCart.tenantSlug}/cart/checkout`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      setPayingOrder(order)
      clear()
    } catch (e: any) {
      if (e.status === 401) {
        setError(t('checkout.loginToCheckout'))
      } else {
        setError(e.message || t('checkout.placeFailed'))
      }
    } finally {
      setSubmitting(false)
    }
  }

  const handlePay = async () => {
    if (!payingOrder) return
    setPayBusy(true)
    setError('')
    try {
      const result = await payOrder(payingOrder.id)
      if (result?.payment?.client_secret) {
        // Real gateway (e.g. Stripe): the order stays "awaiting payment"
        // server-side until its webhook confirms it -- this just switches
        // to the card form that completes the payment client-side.
        setStripePayment({
          clientSecret: result.payment.client_secret,
          publishableKey: result.payment.publishable_key,
        })
      } else {
        // Mock gateway: /pay already marked the order paid synchronously.
        setPaymentDone(true)
      }
    } catch (e: any) {
      setError(e.message || t('checkout.paymentFailed'))
    } finally {
      setPayBusy(false)
    }
  }

  const handleCancelPending = async () => {
    if (!payingOrder) return
    setPayBusy(true)
    setError('')
    try {
      await cancelOrder(payingOrder.id)
      setPayingOrder(null)
    } catch (e: any) {
      setError(e.message || t('checkout.cancelFailed'))
    } finally {
      setPayBusy(false)
    }
  }

  if (loading) {
    return <div className="max-w-4xl mx-auto p-6 text-muted-foreground">{t('checkout.loadingCart')}</div>
  }

  if (payingOrder && paymentDone) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-background min-h-screen">
        <h1 className="text-3xl font-bold mb-8 text-foreground border-b border-border pb-4 font-heading">{t('checkout.title')}</h1>
        <div className="p-4 bg-green-50 text-green-700 rounded-xl border border-green-100 animate-in fade-in-0 zoom-in-95 duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]">
          {t('checkout.paymentSuccess', { number: payingOrder.order_number })}
        </div>
        <div className="mt-6 flex gap-4">
          <button
            onClick={() => router.push('/account/orders')}
            className="bg-primary text-primary-foreground px-6 py-2 rounded-lg font-medium transition-colors duration-150 hover:bg-primary/90 active:scale-[0.98]"
          >
            {t('checkout.viewOrders')}
          </button>
          <button
            onClick={() => router.push(`/store/${activeCart?.tenantSlug}`)}
            className="bg-card border border-border text-foreground px-6 py-2 rounded-lg font-medium transition-colors duration-150 hover:bg-muted active:scale-[0.98]"
          >
            {t('checkout.continueShopping')}
          </button>
        </div>
      </div>
    )
  }

  if (payingOrder) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-background min-h-screen">
        <h1 className="text-3xl font-bold mb-8 text-foreground border-b border-border pb-4 font-heading">{t('checkout.title')}</h1>
        {error && (
          <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100">{error}</div>
        )}
        <div data-testid="pending-payment" className="bg-card p-6 rounded-xl shadow-sm border border-border space-y-4 animate-in fade-in-0 slide-in-from-bottom-2 duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]">
          <div>
            <h2 className="text-xl font-semibold text-foreground">{t('checkout.awaitingPayment', { number: payingOrder.order_number })}</h2>
            <p className="text-muted-foreground mt-1">
              {t('checkout.total')} <span className="font-bold text-foreground">{formatCurrency(Number(payingOrder.total_amount))}</span>
            </p>
            {!stripePayment && (
              <p className="text-sm text-amber-700 mt-2">
                {t('checkout.mockPaymentHint')}
              </p>
            )}
          </div>
          {stripePayment && (
            <StripeCardForm
              clientSecret={stripePayment.clientSecret}
              publishableKey={stripePayment.publishableKey}
              checkPaid={async () => {
                const refreshed = await fetchOrder(payingOrder.id)
                return refreshed.status === 'processing' || refreshed.status === 'completed'
              }}
              onSuccess={() => setPaymentDone(true)}
              onError={(message) => setError(message)}
            />
          )}
          <div className="flex gap-3">
            {!stripePayment && (
              <button
                onClick={handlePay}
                disabled={payBusy}
                className="flex-1 bg-primary text-primary-foreground py-3 rounded-xl font-bold transition-all duration-150 hover:bg-primary/90 active:scale-[0.98] disabled:opacity-70"
              >
                {payBusy ? t('checkout.processing') : t('checkout.payNow')}
              </button>
            )}
            <button
              onClick={handleCancelPending}
              disabled={payBusy}
              className="px-6 py-3 text-destructive border border-destructive/30 rounded-xl font-medium transition-colors duration-150 hover:bg-destructive/10 active:scale-[0.98] disabled:opacity-70"
            >
              {t('checkout.cancelOrder')}
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!activeCart || !cart || cart.items.length === 0) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-background min-h-screen">
        <h1 className="text-3xl font-bold mb-8 text-foreground border-b border-border pb-4 font-heading">{t('checkout.title')}</h1>
        <p className="text-muted-foreground">{t('checkout.empty')}</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-background min-h-screen">
      <h1 className="text-3xl font-bold mb-8 text-foreground border-b border-border pb-4 font-heading">{t('checkout.title')}</h1>

      {error && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2 space-y-6">
          <div data-testid="item-summary" className="bg-card p-6 rounded-xl shadow-sm border border-border">
            <h2 className="text-xl font-semibold mb-4 text-foreground">{t('checkout.itemSummary')}</h2>
            {cart.items.map(item => (
              <div key={item.id} className="flex justify-between items-center py-2 border-b border-border last:border-0 text-foreground/80">
                <span>{item.product_name} &times; {item.quantity}</span>
                <span className="font-medium text-foreground">{formatCurrency(Number(item.total_price))}</span>
              </div>
            ))}
          </div>

          {requiresShippingAddress && (
            <div data-testid="shipping-address-fields" className="bg-card p-6 rounded-xl shadow-sm border border-border">
              <h2 className="text-xl font-semibold mb-4 text-foreground">{t('checkout.shippingDetails')}</h2>
              <div className="space-y-3">
                <div>
                  <label htmlFor="fullName" className="block text-sm font-medium mb-1 text-foreground">{t('checkout.fullName')}</label>
                  <input
                    id="fullName"
                    type="text"
                    className="w-full border border-input rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring outline-none text-foreground transition-shadow"
                    value={fullName}
                    onChange={e => setFullName(e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="checkoutEmail" className="block text-sm font-medium mb-1 text-foreground">{t('checkout.email')}</label>
                  <input
                    id="checkoutEmail"
                    type="email"
                    className="w-full border border-input rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring outline-none text-foreground transition-shadow"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="address" className="block text-sm font-medium mb-1 text-foreground">{t('checkout.address')}</label>
                  <input
                    id="address"
                    type="text"
                    className="w-full border border-input rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring outline-none text-foreground transition-shadow"
                    value={address}
                    onChange={e => setAddress(e.target.value)}
                  />
                </div>
              </div>
            </div>
          )}

          <div data-testid="shipping-methods" className="bg-card p-6 rounded-xl shadow-sm border border-border">
            <h2 className="text-xl font-semibold mb-4 text-foreground">{t('checkout.shippingMethods')}</h2>
            <div className="space-y-3 text-foreground">
              {shippingOptions.map(option => (
                <label key={option.id} className="flex items-center space-x-3 p-3 border border-border rounded-lg hover:bg-accent cursor-pointer transition-colors duration-150">
                  <input
                    type="radio"
                    name="shipping"
                    value={option.id}
                    checked={shippingMethodId === option.id}
                    onChange={() => setShippingMethodId(option.id)}
                    className="text-primary accent-primary"
                  />
                  <span className="font-medium flex-1">{option.name}</span>
                  <span className="text-muted-foreground">{formatCurrency(option.price)}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div data-testid="coupon-input" className="bg-card p-6 rounded-xl shadow-sm border border-border">
            <h2 className="text-xl font-semibold mb-4 text-foreground">{t('checkout.couponCode')}</h2>
            {appliedCoupon ? (
              <div className="flex items-center justify-between bg-green-50 border border-green-100 rounded-lg px-3 py-2">
                <span className="text-green-700 font-medium">{t('checkout.couponApplied', { code: appliedCoupon.code })}</span>
                <button onClick={handleRemoveCoupon} className="text-sm text-destructive hover:underline">{t('checkout.remove')}</button>
              </div>
            ) : (
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder={t('checkout.enterCode')}
                  value={couponInput}
                  onChange={e => setCouponInput(e.target.value)}
                  className="flex-1 border border-input rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring outline-none text-foreground transition-shadow"
                />
                <button
                  onClick={handleApplyCoupon}
                  disabled={applyingCoupon || !couponInput.trim()}
                  className="bg-secondary text-secondary-foreground px-4 py-2 rounded-lg font-medium transition-colors duration-150 hover:bg-secondary/70 active:scale-[0.98] disabled:opacity-50"
                >
                  {applyingCoupon ? t('checkout.applying') : t('checkout.apply')}
                </button>
              </div>
            )}
          </div>

          <div className="bg-card p-6 rounded-xl shadow-sm border border-border">
            <div className="space-y-2 mb-6">
              <div className="flex justify-between text-muted-foreground">
                <span>{t('checkout.subtotal')}</span>
                <span>{formatCurrency(subtotal)}</span>
              </div>
              {appliedCoupon && (
                <div className="flex justify-between text-green-600">
                  <span>{t('checkout.discount', { code: appliedCoupon.code })}</span>
                  <span>-{formatCurrency(discountAmount)}</span>
                </div>
              )}
              {requiresShippingAddress && (
                <div className="flex justify-between text-muted-foreground">
                  <span>{t('checkout.shipping')}</span>
                  <span>{formatCurrency(shippingCost)}</span>
                </div>
              )}
              <div className="flex justify-between font-bold text-xl text-foreground pt-2 border-t border-border">
                <span>{t('checkout.total')}</span>
                <span>{formatCurrency(total)}</span>
              </div>
            </div>
            <button
              onClick={handleCheckout}
              disabled={submitting}
              className="w-full bg-primary text-primary-foreground py-3 rounded-xl font-bold text-lg shadow-lg hover:bg-primary/90 hover:shadow-xl active:scale-[0.98] transition-all duration-150 disabled:opacity-70"
            >
              {submitting ? t('checkout.placing') : t('checkout.placeOrder')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
