'use client'

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getCookie } from 'cookies-next'
import { apiClient } from '@/lib/api/apiClient'
import { getActiveMarketplaceCart } from '@/lib/marketplace-cart'
import { useMarketplaceCart } from '@/context/MarketplaceCartContext'
import { useCurrency } from '@/hooks/useCurrency'
import { orderStatusClass, orderStatusLabel } from '@/lib/orderStatus'
import { StripeCardForm } from '@/components/checkout/StripeCardForm'

interface SubOrder {
  id: number
  tenant_id: number
  order_number: string
  subtotal: number
  total_amount: number
  status: string
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
  const router = useRouter()

  const [isLoggedIn, setIsLoggedIn] = useState<boolean | null>(null)
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

  useEffect(() => {
    setIsLoggedIn(!!getCookie('token'))
  }, [])

  const activeCart = getActiveMarketplaceCart()
  const subtotal = cart ? Number(cart.subtotal) : 0

  const handleCheckout = async () => {
    if (!activeCart || !cart) return
    try {
      setError('')
      setSubmitting(true)

      // Captured before clear() below -- OrderResponse only carries tenant_id,
      // not the vendor's display name, so this is the one place that name is
      // still available once the cart itself is gone.
      const names: Record<number, string> = {}
      for (const item of cart.items) names[item.tenant_id] = item.tenant_name
      setVendorNames(names)

      const order: MasterOrder = await apiClient('/api/v1/marketplace/checkout', {
        method: 'POST',
        body: JSON.stringify({
          cart_id: activeCart.cartId,
          payment_token: crypto.randomUUID(),
          shipping_address: { full_name: fullName, email, address_line_1: address },
        }),
      })

      setMasterOrder(order)
      clear()
    } catch (e: any) {
      if (e.status === 401) {
        setError('Please log in to complete checkout.')
      } else {
        setError(e.message || 'Failed to place order.')
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
    } catch (e: any) {
      setError(e.message || 'Payment failed.')
    } finally {
      setPayBusy(false)
    }
  }

  if (isLoggedIn === false) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-background min-h-screen">
        <h1 className="text-3xl font-bold mb-8 text-foreground border-b border-border pb-4 font-heading">Checkout</h1>
        <div className="bg-card p-6 rounded-xl shadow-sm border border-border">
          <p className="text-foreground/80">You need to be logged in to check out across the marketplace.</p>
          <button
            onClick={() => router.push('/login')}
            className="mt-4 bg-primary text-primary-foreground px-6 py-2 rounded-lg font-medium transition-colors duration-150 hover:bg-primary/90 active:scale-[0.98]"
          >
            Log In
          </button>
        </div>
      </div>
    )
  }

  if (loading || isLoggedIn === null) {
    return <div className="max-w-4xl mx-auto p-6 text-muted-foreground">Loading your cart...</div>
  }

  if (masterOrder && paymentDone) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-background min-h-screen">
        <h1 className="text-3xl font-bold mb-8 text-foreground border-b border-border pb-4 font-heading">Checkout</h1>
        <div className="p-4 bg-green-50 text-green-700 rounded-xl border border-green-100 animate-in fade-in-0 zoom-in-95 duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]">
          Payment successful! Order #{masterOrder.master_order_number} is now being processed, split across{' '}
          {masterOrder.sub_orders.length} vendor{masterOrder.sub_orders.length === 1 ? '' : 's'}.
        </div>
        <div data-testid="master-order-sub-orders" className="mt-6 space-y-3">
          {masterOrder.sub_orders.map(so => (
            <div key={so.id} className="bg-card p-4 rounded-xl shadow-sm border border-border flex items-center justify-between">
              <div>
                <div className="font-semibold text-foreground">{vendorNames[so.tenant_id] || `Vendor #${so.tenant_id}`}</div>
                <div className="text-sm text-muted-foreground">Order #{so.order_number}</div>
              </div>
              <div className="text-right">
                <div className="font-semibold text-foreground">{formatCurrency(Number(so.total_amount))}</div>
                <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${orderStatusClass[so.status]}`}>
                  {orderStatusLabel[so.status] || so.status}
                </span>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-6 flex gap-4">
          <button
            onClick={() => router.push('/account/orders')}
            className="bg-primary text-primary-foreground px-6 py-2 rounded-lg font-medium transition-colors duration-150 hover:bg-primary/90 active:scale-[0.98]"
          >
            View My Orders
          </button>
          <button
            onClick={() => router.push('/marketplace')}
            className="bg-card border border-border text-foreground px-6 py-2 rounded-lg font-medium transition-colors duration-150 hover:bg-muted active:scale-[0.98]"
          >
            Continue Shopping
          </button>
        </div>
      </div>
    )
  }

  if (masterOrder) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-background min-h-screen">
        <h1 className="text-3xl font-bold mb-8 text-foreground border-b border-border pb-4 font-heading">Checkout</h1>
        {error && <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100">{error}</div>}
        <div data-testid="pending-payment" className="bg-card p-6 rounded-xl shadow-sm border border-border space-y-4 animate-in fade-in-0 slide-in-from-bottom-2 duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]">
          <div>
            <h2 className="text-xl font-semibold text-foreground">Order #{masterOrder.master_order_number} is awaiting payment</h2>
            <p className="text-muted-foreground mt-1">
              Total: <span className="font-bold text-foreground">{formatCurrency(Number(masterOrder.total_amount))}</span>
            </p>
            {!stripePayment && (
              <p className="text-sm text-amber-700 mt-2">
                This is a development environment — payment is simulated. Unpaid orders are automatically
                cancelled and their stock released if left pending too long.
              </p>
            )}
          </div>
          <div data-testid="master-order-sub-orders" className="space-y-2">
            {masterOrder.sub_orders.map(so => (
              <div key={so.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
                <div>
                  <div className="text-sm font-medium text-foreground">{vendorNames[so.tenant_id] || `Vendor #${so.tenant_id}`}</div>
                  <div className="text-xs text-muted-foreground">Order #{so.order_number}</div>
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
              {payBusy ? 'Processing...' : 'Pay Now'}
            </button>
          )}
        </div>
      </div>
    )
  }

  if (!activeCart || !cart || cart.items.length === 0) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-background min-h-screen">
        <h1 className="text-3xl font-bold mb-8 text-foreground border-b border-border pb-4 font-heading">Checkout</h1>
        <p className="text-muted-foreground">Your marketplace cart is empty. Add items from the marketplace first.</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-background min-h-screen">
      <h1 className="text-3xl font-bold mb-8 text-foreground border-b border-border pb-4 font-heading">Checkout</h1>

      {error && <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2 space-y-6">
          <div data-testid="item-summary" className="bg-card p-6 rounded-xl shadow-sm border border-border">
            <h2 className="text-xl font-semibold mb-4 text-foreground">
              Item Summary &middot; {cart.vendor_count} vendor{cart.vendor_count === 1 ? '' : 's'}
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
              This will be placed as {cart.vendor_count} separate order{cart.vendor_count === 1 ? '' : 's'}, one per vendor.
            </p>
          </div>

          <div data-testid="shipping-address-fields" className="bg-card p-6 rounded-xl shadow-sm border border-border">
            <h2 className="text-xl font-semibold mb-4 text-foreground">Shipping Details</h2>
            <div className="space-y-3">
              <div>
                <label htmlFor="mpFullName" className="block text-sm font-medium mb-1 text-foreground">Full Name</label>
                <input
                  id="mpFullName"
                  type="text"
                  className="w-full border border-input rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring outline-none text-foreground transition-shadow"
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="mpEmail" className="block text-sm font-medium mb-1 text-foreground">Email</label>
                <input
                  id="mpEmail"
                  type="email"
                  className="w-full border border-input rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring outline-none text-foreground transition-shadow"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="mpAddress" className="block text-sm font-medium mb-1 text-foreground">Address</label>
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
        </div>

        <div className="space-y-6">
          <div className="bg-card p-6 rounded-xl shadow-sm border border-border">
            <div className="space-y-2 mb-6">
              <div className="flex justify-between text-muted-foreground">
                <span>Subtotal:</span>
                <span>{formatCurrency(subtotal)}</span>
              </div>
              <div className="flex justify-between font-bold text-xl text-foreground pt-2 border-t border-border">
                <span>Total:</span>
                <span>{formatCurrency(subtotal)}</span>
              </div>
            </div>
            <button
              onClick={handleCheckout}
              disabled={submitting}
              className="w-full bg-primary text-primary-foreground py-3 rounded-xl font-bold text-lg shadow-lg hover:bg-primary/90 hover:shadow-xl active:scale-[0.98] transition-all duration-150 disabled:opacity-70"
            >
              {submitting ? 'Placing Order...' : 'Place Order'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
