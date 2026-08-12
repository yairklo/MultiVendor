'use client'

import React, { useState } from 'react'
import { apiClient } from '@/lib/api/apiClient'
import { getActiveCart } from '@/lib/cart'
import { useCart } from '@/context/CartContext'
import { useOrders } from '@/hooks/useOrders'
import { useToast } from '@/context/ToastContext'
import { useCurrency } from '@/hooks/useCurrency'
import { useRouter } from 'next/navigation'

const shippingOptions = [
  { id: 1, name: 'Standard Shipping (3-5 days)', price: 5 },
  { id: 2, name: 'Express Shipping (1-2 days)', price: 15 }
]

export default function CheckoutPage() {
  const { cart, loading, clear } = useCart()
  const { formatCurrency } = useCurrency()
  const { payOrder, cancelOrder } = useOrders()
  const { showToast } = useToast()
  const [error, setError] = useState<string>('')
  const [submitting, setSubmitting] = useState(false)
  const [payingOrder, setPayingOrder] = useState<any>(null)
  const [paymentDone, setPaymentDone] = useState(false)
  const [payBusy, setPayBusy] = useState(false)
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
      showToast(`Coupon "${coupon.code}" applied`, 'success')
    } catch (e: any) {
      showToast(e.message || 'Invalid or expired coupon', 'error')
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
        setError('Please log in to complete checkout.')
      } else {
        setError(e.message || 'Failed to place order.')
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
      await payOrder(payingOrder.id)
      setPaymentDone(true)
    } catch (e: any) {
      setError(e.message || 'Payment failed.')
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
      setError(e.message || 'Failed to cancel order.')
    } finally {
      setPayBusy(false)
    }
  }

  if (loading) {
    return <div className="max-w-4xl mx-auto p-6 text-gray-600">Loading your cart...</div>
  }

  if (payingOrder && paymentDone) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-gray-50 min-h-screen">
        <h1 className="text-3xl font-bold mb-4 text-gray-900 border-b pb-4">Checkout</h1>
        <div className="p-4 bg-green-50 text-green-700 rounded-lg border border-green-100">
          Payment successful! Order #{payingOrder.order_number} is now being processed.
        </div>
        <div className="mt-6 flex gap-4">
          <button
            onClick={() => router.push('/account/orders')}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700"
          >
            View My Orders
          </button>
          <button
            onClick={() => router.push(`/store/${activeCart?.tenantSlug}`)}
            className="bg-white border border-gray-300 text-gray-800 px-6 py-2 rounded-lg font-medium hover:bg-gray-50"
          >
            Continue Shopping
          </button>
        </div>
      </div>
    )
  }

  if (payingOrder) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-gray-50 min-h-screen">
        <h1 className="text-3xl font-bold mb-4 text-gray-900 border-b pb-4">Checkout</h1>
        {error && (
          <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">{error}</div>
        )}
        <div data-testid="pending-payment" className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 space-y-4">
          <div>
            <h2 className="text-xl font-semibold">Order #{payingOrder.order_number} is awaiting payment</h2>
            <p className="text-gray-600 mt-1">
              Total: <span className="font-bold">{formatCurrency(Number(payingOrder.total_amount))}</span>
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handlePay}
              disabled={payBusy}
              className="flex-1 bg-blue-600 text-white py-3 rounded-xl font-bold hover:bg-blue-700 disabled:opacity-70"
            >
              {payBusy ? 'Processing...' : 'Pay Now'}
            </button>
            <button
              onClick={handleCancelPending}
              disabled={payBusy}
              className="px-6 py-3 text-red-600 border border-red-200 rounded-xl font-medium hover:bg-red-50 disabled:opacity-70"
            >
              Cancel Order
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!activeCart || !cart || cart.items.length === 0) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-gray-50 min-h-screen">
        <h1 className="text-3xl font-bold mb-4 text-gray-900 border-b pb-4">Checkout</h1>
        <p className="text-gray-600">Your cart is empty. Add items from the storefront first.</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-gray-50 min-h-screen">
      <h1 className="text-3xl font-bold mb-8 text-gray-900 border-b pb-4">Checkout</h1>

      {error && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2 space-y-6">
          <div data-testid="item-summary" className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <h2 className="text-xl font-semibold mb-4">Item Summary</h2>
            {cart.items.map(item => (
              <div key={item.id} className="flex justify-between items-center py-2 border-b text-gray-700">
                <span>{item.product_name} &times; {item.quantity}</span>
                <span className="font-medium">{formatCurrency(Number(item.total_price))}</span>
              </div>
            ))}
          </div>

          {requiresShippingAddress && (
            <div data-testid="shipping-address-fields" className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
              <h2 className="text-xl font-semibold mb-4">Shipping Details</h2>
              <div className="space-y-3">
                <div>
                  <label htmlFor="fullName" className="block text-sm font-medium mb-1">Full Name</label>
                  <input
                    id="fullName"
                    type="text"
                    className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-600 outline-none text-gray-800"
                    value={fullName}
                    onChange={e => setFullName(e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="checkoutEmail" className="block text-sm font-medium mb-1">Email</label>
                  <input
                    id="checkoutEmail"
                    type="email"
                    className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-600 outline-none text-gray-800"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="address" className="block text-sm font-medium mb-1">Address</label>
                  <input
                    id="address"
                    type="text"
                    className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-600 outline-none text-gray-800"
                    value={address}
                    onChange={e => setAddress(e.target.value)}
                  />
                </div>
              </div>
            </div>
          )}

          <div data-testid="shipping-methods" className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <h2 className="text-xl font-semibold mb-4">Shipping Methods</h2>
            <div className="space-y-3 text-gray-800">
              {shippingOptions.map(option => (
                <label key={option.id} className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-blue-50 cursor-pointer transition-colors">
                  <input 
                    type="radio" 
                    name="shipping" 
                    value={option.id} 
                    checked={shippingMethodId === option.id}
                    onChange={() => setShippingMethodId(option.id)}
                    className="text-blue-600" 
                  />
                  <span className="font-medium flex-1">{option.name}</span>
                  <span className="text-gray-600">{formatCurrency(option.price)}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div data-testid="coupon-input" className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <h2 className="text-xl font-semibold mb-4">Coupon Code</h2>
            {appliedCoupon ? (
              <div className="flex items-center justify-between bg-green-50 border border-green-100 rounded-lg px-3 py-2">
                <span className="text-green-700 font-medium">{appliedCoupon.code} applied</span>
                <button onClick={handleRemoveCoupon} className="text-sm text-red-600 hover:underline">Remove</button>
              </div>
            ) : (
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Enter code"
                  value={couponInput}
                  onChange={e => setCouponInput(e.target.value)}
                  className="flex-1 border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-600 outline-none text-gray-800"
                />
                <button
                  onClick={handleApplyCoupon}
                  disabled={applyingCoupon || !couponInput.trim()}
                  className="bg-gray-800 text-white px-4 py-2 rounded-lg font-medium hover:bg-gray-900 transition-colors disabled:opacity-50"
                >
                  {applyingCoupon ? 'Applying...' : 'Apply'}
                </button>
              </div>
            )}
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <div className="space-y-2 mb-6">
              <div className="flex justify-between text-gray-600">
                <span>Subtotal:</span>
                <span>{formatCurrency(subtotal)}</span>
              </div>
              {appliedCoupon && (
                <div className="flex justify-between text-green-600">
                  <span>Discount ({appliedCoupon.code}):</span>
                  <span>-{formatCurrency(discountAmount)}</span>
                </div>
              )}
              {requiresShippingAddress && (
                <div className="flex justify-between text-gray-600">
                  <span>Shipping:</span>
                  <span>${shippingCost.toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between font-bold text-xl text-gray-900 pt-2 border-t">
                <span>Total:</span>
                <span>{formatCurrency(total)}</span>
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
