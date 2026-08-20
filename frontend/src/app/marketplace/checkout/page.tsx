'use client'

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getCookie } from 'cookies-next'
import { apiClient } from '@/lib/api/apiClient'
import { getActiveMarketplaceCart } from '@/lib/marketplace-cart'
import { useMarketplaceCart } from '@/context/MarketplaceCartContext'
import { useCurrency } from '@/hooks/useCurrency'
import { orderStatusClass, orderStatusLabel } from '@/lib/orderStatus'

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
      setPaymentDone(true)
    } catch (e: any) {
      setError(e.message || 'Payment failed.')
    } finally {
      setPayBusy(false)
    }
  }

  if (isLoggedIn === false) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-gray-50 min-h-screen">
        <h1 className="text-3xl font-bold mb-4 text-gray-900 border-b pb-4">Checkout</h1>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <p className="text-gray-700">You need to be logged in to check out across the marketplace.</p>
          <button
            onClick={() => router.push('/login')}
            className="mt-4 bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700"
          >
            Log In
          </button>
        </div>
      </div>
    )
  }

  if (loading || isLoggedIn === null) {
    return <div className="max-w-4xl mx-auto p-6 text-gray-600">Loading your cart...</div>
  }

  if (masterOrder && paymentDone) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-gray-50 min-h-screen">
        <h1 className="text-3xl font-bold mb-4 text-gray-900 border-b pb-4">Checkout</h1>
        <div className="p-4 bg-green-50 text-green-700 rounded-lg border border-green-100">
          Payment successful! Order #{masterOrder.master_order_number} is now being processed, split across{' '}
          {masterOrder.sub_orders.length} vendor{masterOrder.sub_orders.length === 1 ? '' : 's'}.
        </div>
        <div data-testid="master-order-sub-orders" className="mt-6 space-y-3">
          {masterOrder.sub_orders.map(so => (
            <div key={so.id} className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
              <div>
                <div className="font-semibold text-gray-900">{vendorNames[so.tenant_id] || `Vendor #${so.tenant_id}`}</div>
                <div className="text-sm text-gray-500">Order #{so.order_number}</div>
              </div>
              <div className="text-right">
                <div className="font-semibold text-gray-900">{formatCurrency(Number(so.total_amount))}</div>
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
            className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700"
          >
            View My Orders
          </button>
          <button
            onClick={() => router.push('/marketplace')}
            className="bg-white border border-gray-300 text-gray-800 px-6 py-2 rounded-lg font-medium hover:bg-gray-50"
          >
            Continue Shopping
          </button>
        </div>
      </div>
    )
  }

  if (masterOrder) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-gray-50 min-h-screen">
        <h1 className="text-3xl font-bold mb-4 text-gray-900 border-b pb-4">Checkout</h1>
        {error && <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">{error}</div>}
        <div data-testid="pending-payment" className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 space-y-4">
          <div>
            <h2 className="text-xl font-semibold">Order #{masterOrder.master_order_number} is awaiting payment</h2>
            <p className="text-gray-600 mt-1">
              Total: <span className="font-bold">{formatCurrency(Number(masterOrder.total_amount))}</span>
            </p>
            <p className="text-sm text-amber-700 mt-2">
              This is a development environment — payment is simulated. Unpaid orders are automatically
              cancelled and their stock released if left pending too long.
            </p>
          </div>
          <div data-testid="master-order-sub-orders" className="space-y-2">
            {masterOrder.sub_orders.map(so => (
              <div key={so.id} className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2">
                <div>
                  <div className="text-sm font-medium text-gray-900">{vendorNames[so.tenant_id] || `Vendor #${so.tenant_id}`}</div>
                  <div className="text-xs text-gray-500">Order #{so.order_number}</div>
                </div>
                <div className="text-sm font-semibold text-gray-700">{formatCurrency(Number(so.total_amount))}</div>
              </div>
            ))}
          </div>
          <button
            onClick={handlePay}
            disabled={payBusy}
            className="w-full bg-blue-600 text-white py-3 rounded-xl font-bold hover:bg-blue-700 disabled:opacity-70"
          >
            {payBusy ? 'Processing...' : 'Pay Now'}
          </button>
        </div>
      </div>
    )
  }

  if (!activeCart || !cart || cart.items.length === 0) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-gray-50 min-h-screen">
        <h1 className="text-3xl font-bold mb-4 text-gray-900 border-b pb-4">Checkout</h1>
        <p className="text-gray-600">Your marketplace cart is empty. Add items from the marketplace first.</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-gray-50 min-h-screen">
      <h1 className="text-3xl font-bold mb-8 text-gray-900 border-b pb-4">Checkout</h1>

      {error && <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2 space-y-6">
          <div data-testid="item-summary" className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <h2 className="text-xl font-semibold mb-4">
              Item Summary &middot; {cart.vendor_count} vendor{cart.vendor_count === 1 ? '' : 's'}
            </h2>
            {cart.items.map(item => (
              <div key={item.id} className="flex justify-between items-center py-2 border-b text-gray-700">
                <span>
                  {item.product_name} &times; {item.quantity}
                  <span className="ml-2 text-xs text-gray-400">({item.tenant_name})</span>
                </span>
                <span className="font-medium">{formatCurrency(Number(item.total_price))}</span>
              </div>
            ))}
            <p className="mt-3 text-xs text-gray-500">
              This will be placed as {cart.vendor_count} separate order{cart.vendor_count === 1 ? '' : 's'}, one per vendor.
            </p>
          </div>

          <div data-testid="shipping-address-fields" className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <h2 className="text-xl font-semibold mb-4">Shipping Details</h2>
            <div className="space-y-3">
              <div>
                <label htmlFor="mpFullName" className="block text-sm font-medium mb-1">Full Name</label>
                <input
                  id="mpFullName"
                  type="text"
                  className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-600 outline-none text-gray-800"
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="mpEmail" className="block text-sm font-medium mb-1">Email</label>
                <input
                  id="mpEmail"
                  type="email"
                  className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-600 outline-none text-gray-800"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="mpAddress" className="block text-sm font-medium mb-1">Address</label>
                <input
                  id="mpAddress"
                  type="text"
                  className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-600 outline-none text-gray-800"
                  value={address}
                  onChange={e => setAddress(e.target.value)}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <div className="space-y-2 mb-6">
              <div className="flex justify-between text-gray-600">
                <span>Subtotal:</span>
                <span>{formatCurrency(subtotal)}</span>
              </div>
              <div className="flex justify-between font-bold text-xl text-gray-900 pt-2 border-t">
                <span>Total:</span>
                <span>{formatCurrency(subtotal)}</span>
              </div>
            </div>
            <button
              onClick={handleCheckout}
              disabled={submitting}
              className="w-full bg-blue-600 text-white py-3 rounded-xl font-bold text-lg hover:bg-blue-700 shadow-lg hover:shadow-xl active:scale-[0.98] transition-all disabled:opacity-70"
            >
              {submitting ? 'Placing Order...' : 'Place Order'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
