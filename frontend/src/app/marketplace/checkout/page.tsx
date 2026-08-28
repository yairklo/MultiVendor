'use client'

import React, { useState, useSyncExternalStore } from 'react'
import { useRouter } from 'next/navigation'
import { getCookie } from 'cookies-next'
import { apiClient, ApiError } from '@/lib/api/apiClient'
import { getActiveMarketplaceCart } from '@/lib/marketplace-cart'
import { useMarketplaceCart } from '@/context/MarketplaceCartContext'
import { useCurrency } from '@/hooks/useCurrency'
import { orderStatusClass, orderStatusLabel } from '@/lib/orderStatus'
import { StripeCardForm } from '@/components/checkout/StripeCardForm'
import { DigitalDownloads } from '@/components/orders/DigitalDownloads'
import { useUiLocale } from '@/context/UiLocaleContext'
import { errorMessage } from '@/lib/errors'

// Same SSR/hydration-safe cookie read as useTenantSlug -- see that hook for why
// a plain useEffect+useState pair isn't used here. Server/first-client-render
// snapshot is null ("not checked yet"), distinct from false ("checked, logged
// out") -- the render logic below treats only null as still-loading.
function subscribeNoop(): () => void {
  return () => {}
}
function getLoggedInSnapshot(): boolean | null {
  return !!getCookie('token')
}
function getLoggedInServerSnapshot(): boolean | null {
  return null
}

interface SubOrder {
  id: number
  tenant_id: number
  order_number: string
  subtotal: number
  total_amount: number
  status: string
  items?: { id: number; product_name?: string; download_url?: string | null }[]
}

interface MasterOrder {
  id: number
  master_order_number: string
  total_amount: number
  sub_orders: SubOrder[]
  payment?: { provider: string; client_secret: string; publishable_key: string | null } | null
}

/**
 * Full-page checkout for the cross-vendor marketplace cart, mirroring
 * app/checkout/page.tsx's shape (item summary -> shipping -> place order ->
 * awaiting-payment -> paid confirmation) but simplified for what the
 * marketplace checkout endpoint actually supports: no coupon, no shipping
 * method choice (backend always charges 0 shipping for a marketplace
 * sub-order today), and the result is N sub-orders (one per vendor) under
 * one master order instead of a single order.
 */
export default function MarketplaceCheckoutPage() {
  const { cart, loading, clear } = useMarketplaceCart()
  const { formatCurrency } = useCurrency()
  const { t } = useUiLocale()
  const router = useRouter()

  const isLoggedIn = useSyncExternalStore(subscribeNoop, getLoggedInSnapshot, getLoggedInServerSnapshot)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [masterOrder, setMasterOrder] = useState<MasterOrder | null>(null)
  const [paymentDone, setPaymentDone] = useState(false)
  const [payBusy, setPayBusy] = useState(false)
  const [stripePayment, setStripePayment] = useState<{ clientSecret: string; publishableKey: string } | null>(null)
  const [vendorNames, setVendorNames] = useState<Record<number, string>>({})
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [address, setAddress] = useState('')
  const [city, setCity] = useState('')
  const [phone, setPhone] = useState('')

  const activeCart = getActiveMarketplaceCart()
  const subtotal = cart ? Number(cart.subtotal) : 0

  const isDigitalOnly = !!cart && cart.items.length > 0 && cart.items.every(item => item.product_type === 'digital')
  const requiresShippingAddress = !!cart && cart.items.length > 0 && !isDigitalOnly

  const handleCheckout = async () => {
    if (!activeCart || !cart) return
    if (requiresShippingAddress && (!fullName.trim() || !city.trim() || !address.trim() || !phone.trim())) {
      setError(t('checkout.shippingFieldsRequired'))
      return
    }
    try {
      setError('')
      setSubmitting(true)

      // Captured before clear() below -- OrderResponse only carries tenant_id,
      // not the vendor's display name, so this is the one place that name is
      // still available once the cart itself is gone.
      const names: Record<number, string> = {}
      for (const item of cart.items) names[item.tenant_id] = item.tenant_name
      setVendorNames(names)

      const payload: Record<string, unknown> = {
        cart_id: activeCart.cartId,
        payment_token: crypto.randomUUID(),
      }
      if (requiresShippingAddress) {
        payload.shipping_address = { full_name: fullName, email, phone, city, address_line_1: address }
      }

      const order: MasterOrder = await apiClient('/api/v1/marketplace/checkout', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      setMasterOrder(order)
      clear()
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setError(t('checkout.loginToCheckout'))
      } else {
        setError(errorMessage(e) || t('checkout.placeFailed'))
      }
    } finally {
      setSubmitting(false)
    }
  }

  const handlePay = async () => {
    if (!masterOrder) return
    setPayBusy(true)
    setError('')
    try {
      const updated = await apiClient(`/api/v1/marketplace/orders/${masterOrder.id}/pay`, { method: 'POST' })
      setMasterOrder(updated)
      if (updated?.payment?.client_secret) {
        // Real gateway (e.g. Stripe): sub-orders stay "awaiting payment"
        // server-side until the shared webhook confirms them -- this just
        // switches to the card form that completes the payment client-side.
        setStripePayment({
          clientSecret: updated.payment.client_secret,
          publishableKey: updated.payment.publishable_key,
        })
      } else {
        // Mock gateway: /pay already marked every sub-order paid synchronously.
        setPaymentDone(true)
      }
    } catch (e) {
      setError(errorMessage(e) || t('checkout.paymentFailed'))
    } finally {
      setPayBusy(false)
    }
  }

  if (isLoggedIn === false) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-background min-h-screen">
        <h1 className="text-3xl font-bold mb-8 text-foreground border-b border-border pb-4 font-heading">{t('checkout.title')}</h1>
        <div className="bg-card p-6 rounded-xl shadow-sm border border-border">
          <p className="text-foreground/80">{t('checkout.loginRequiredMarketplace')}</p>
          <button
            onClick={() => router.push('/login')}
            className="mt-4 bg-primary text-primary-foreground px-6 py-2 rounded-lg font-medium transition-colors duration-150 hover:bg-primary/90 active:scale-[0.98]"
          >
            {t('common.login')}
          </button>
        </div>
      </div>
    )
  }

  if (loading || isLoggedIn === null) {
    return <div className="max-w-4xl mx-auto p-6 text-muted-foreground">{t('checkout.loadingCart')}</div>
  }

  if (masterOrder && paymentDone) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-background min-h-screen">
        <h1 className="text-3xl font-bold mb-8 text-foreground border-b border-border pb-4 font-heading">{t('checkout.title')}</h1>
        <div className="p-4 bg-green-50 text-green-700 rounded-xl border border-green-100 animate-in fade-in-0 zoom-in-95 duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]">
          {t('checkout.paymentSuccessMarketplace', { number: masterOrder.master_order_number, count: masterOrder.sub_orders.length })}
        </div>
        <div data-testid="master-order-sub-orders" className="mt-6 space-y-3">
          {masterOrder.sub_orders.map(so => (
            <div key={so.id} className="bg-card p-4 rounded-xl shadow-sm border border-border flex items-center justify-between">
              <div>
                <div className="font-semibold text-foreground">{vendorNames[so.tenant_id] || t('checkout.vendor', { id: so.tenant_id })}</div>
                <div className="text-sm text-muted-foreground">{t('checkout.orderNumber', { number: so.order_number })}</div>
              </div>
              <div className="text-right">
                <div className="font-semibold text-foreground">{formatCurrency(Number(so.total_amount))}</div>
                <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${orderStatusClass[so.status]}`}>
                  {orderStatusLabel[so.status] ? t(`orderStatus.${so.status}`) : so.status}
                </span>
              </div>
            </div>
          ))}
        </div>
        <DigitalDownloads
          items={masterOrder.sub_orders.flatMap((so) => so.items || [])}
          heading={t('checkout.downloadsHeading')}
          label={t('checkout.downloadFile')}
        />
        <div className="mt-6 flex gap-4">
          <button
            onClick={() => router.push('/account/orders')}
            className="bg-primary text-primary-foreground px-6 py-2 rounded-lg font-medium transition-colors duration-150 hover:bg-primary/90 active:scale-[0.98]"
          >
            {t('checkout.viewOrders')}
          </button>
          <button
            onClick={() => router.push('/marketplace')}
            className="bg-card border border-border text-foreground px-6 py-2 rounded-lg font-medium transition-colors duration-150 hover:bg-muted active:scale-[0.98]"
          >
            {t('checkout.continueShopping')}
          </button>
        </div>
      </div>
    )
  }

  if (masterOrder) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-background min-h-screen">
        <h1 className="text-3xl font-bold mb-8 text-foreground border-b border-border pb-4 font-heading">{t('checkout.title')}</h1>
        {error && <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100">{error}</div>}
        <div data-testid="pending-payment" className="bg-card p-6 rounded-xl shadow-sm border border-border space-y-4 animate-in fade-in-0 slide-in-from-bottom-2 duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]">
          <div>
            <h2 className="text-xl font-semibold text-foreground">{t('checkout.awaitingPayment', { number: masterOrder.master_order_number })}</h2>
            <p className="text-muted-foreground mt-1">
              {t('checkout.total')} <span className="font-bold text-foreground">{formatCurrency(Number(masterOrder.total_amount))}</span>
            </p>
            {!stripePayment && (
              <p className="text-sm text-amber-700 mt-2">
                {t('checkout.mockPaymentHint')}
              </p>
            )}
          </div>
          <div data-testid="master-order-sub-orders" className="space-y-2">
            {masterOrder.sub_orders.map(so => (
              <div key={so.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
                <div>
                  <div className="text-sm font-medium text-foreground">{vendorNames[so.tenant_id] || t('checkout.vendor', { id: so.tenant_id })}</div>
                  <div className="text-xs text-muted-foreground">{t('checkout.orderNumber', { number: so.order_number })}</div>
                </div>
                <div className="text-sm font-semibold text-foreground/80">{formatCurrency(Number(so.total_amount))}</div>
              </div>
            ))}
          </div>
          {stripePayment ? (
            <StripeCardForm
              clientSecret={stripePayment.clientSecret}
              publishableKey={stripePayment.publishableKey}
              checkPaid={async () => {
                const refreshed: MasterOrder = await apiClient(`/api/v1/marketplace/orders/${masterOrder.id}`)
                setMasterOrder(refreshed)
                return refreshed.sub_orders.every(so => so.status === 'processing' || so.status === 'completed')
              }}
              onSuccess={() => setPaymentDone(true)}
              onError={(message) => setError(message)}
            />
          ) : (
            <button
              onClick={handlePay}
              disabled={payBusy}
              className="w-full bg-primary text-primary-foreground py-3 rounded-xl font-bold transition-all duration-150 hover:bg-primary/90 active:scale-[0.98] disabled:opacity-70"
            >
              {payBusy ? t('checkout.processing') : t('checkout.payNow')}
            </button>
          )}
        </div>
      </div>
    )
  }

  if (!activeCart || !cart || cart.items.length === 0) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-background min-h-screen">
        <h1 className="text-3xl font-bold mb-8 text-foreground border-b border-border pb-4 font-heading">{t('checkout.title')}</h1>
        <p className="text-muted-foreground">{t('checkout.emptyMarketplace')}</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-background min-h-screen">
      <h1 className="text-3xl font-bold mb-8 text-foreground border-b border-border pb-4 font-heading">{t('checkout.title')}</h1>

      {error && <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2 space-y-6">
          <div data-testid="item-summary" className="bg-card p-6 rounded-xl shadow-sm border border-border">
            <h2 className="text-xl font-semibold mb-4 text-foreground">
              {t('checkout.itemSummaryVendors', { count: cart.vendor_count })}
            </h2>
            {cart.items.map(item => (
              <div key={item.id} className="flex justify-between items-center py-2 border-b border-border last:border-0 text-foreground/80">
                <span>
                  {item.product_name} &times; {item.quantity}
                  <span className="ml-2 text-xs text-muted-foreground">({item.tenant_name})</span>
                </span>
                <span className="font-medium text-foreground">{formatCurrency(Number(item.total_price))}</span>
              </div>
            ))}
            <p className="mt-3 text-xs text-muted-foreground">
              {t('checkout.splitOrders', { count: cart.vendor_count })}
            </p>
          </div>

          {requiresShippingAddress && (
            <div data-testid="shipping-address-fields" className="bg-card p-6 rounded-xl shadow-sm border border-border">
              <h2 className="text-xl font-semibold mb-4 text-foreground">{t('checkout.shippingDetails')}</h2>
              <div className="space-y-3">
                <div>
                  <label htmlFor="mpFullName" className="block text-sm font-medium mb-1 text-foreground">{t('checkout.fullName')}</label>
                  <input
                    id="mpFullName"
                    type="text"
                    className="w-full border border-input rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring outline-none text-foreground transition-shadow"
                    value={fullName}
                    onChange={e => setFullName(e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="mpEmail" className="block text-sm font-medium mb-1 text-foreground">{t('checkout.email')}</label>
                  <input
                    id="mpEmail"
                    type="email"
                    className="w-full border border-input rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring outline-none text-foreground transition-shadow"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="mpPhone" className="block text-sm font-medium mb-1 text-foreground">{t('checkout.phone')}</label>
                  <input
                    id="mpPhone"
                    type="tel"
                    className="w-full border border-input rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring outline-none text-foreground transition-shadow"
                    value={phone}
                    onChange={e => setPhone(e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="mpCity" className="block text-sm font-medium mb-1 text-foreground">{t('checkout.city')}</label>
                  <input
                    id="mpCity"
                    type="text"
                    className="w-full border border-input rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring outline-none text-foreground transition-shadow"
                    value={city}
                    onChange={e => setCity(e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="mpAddress" className="block text-sm font-medium mb-1 text-foreground">{t('checkout.address')}</label>
                  <input
                    id="mpAddress"
                    type="text"
                    className="w-full border border-input rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring outline-none text-foreground transition-shadow"
                    value={address}
                    onChange={e => setAddress(e.target.value)}
                  />
                </div>
              </div>
            </div>
          )}
          {isDigitalOnly && (
            <p className="rounded-xl border border-border bg-card px-4 py-3 text-sm text-muted-foreground">
              {t('checkout.digitalNoShipping')}
            </p>
          )}
        </div>

        <div className="space-y-6">
          <div className="bg-card p-6 rounded-xl shadow-sm border border-border">
            <div className="space-y-2 mb-6">
              <div className="flex justify-between text-muted-foreground">
                <span>{t('checkout.subtotal')}</span>
                <span>{formatCurrency(subtotal)}</span>
              </div>
              <div className="flex justify-between font-bold text-xl text-foreground pt-2 border-t border-border">
                <span>{t('checkout.total')}</span>
                <span>{formatCurrency(subtotal)}</span>
              </div>
            </div>
            <button
              onClick={handleCheckout}
              disabled={submitting || (requiresShippingAddress && (!fullName.trim() || !city.trim() || !address.trim() || !phone.trim()))}
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
