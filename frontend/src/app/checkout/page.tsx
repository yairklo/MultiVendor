'use client'

import React, { useState } from 'react'
import { apiClient } from '@/lib/api/apiClient'
import { getActiveCart } from '@/lib/cart'
import { useCart } from '@/context/CartContext'

export default function CheckoutPage() {
  const { cart, loading, clear } = useCart()
  const [status, setStatus] = useState<string>('')
  const [error, setError] = useState<string>('')
  const [submitting, setSubmitting] = useState(false)
  const [orderPlaced, setOrderPlaced] = useState(false)
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [address, setAddress] = useState('')

  const activeCart = getActiveCart()

  const isDigitalOnly = !!cart && cart.items.length > 0 && cart.items.every(item => item.product_type !== 'physical')
  const requiresShippingAddress = !!cart && cart.items.length > 0 && !isDigitalOnly

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
      }

      await apiClient(`/api/v1/store/${activeCart.tenantSlug}/cart/checkout`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      setStatus('Order placed successfully!')
      setOrderPlaced(true)
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

  if (loading) {
    return <div className="max-w-4xl mx-auto p-6 text-gray-600">Loading your cart...</div>
  }

  if (orderPlaced) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-gray-50 min-h-screen">
        <h1 className="text-3xl font-bold mb-4 text-gray-900 border-b pb-4">Checkout</h1>
        <div className="p-4 bg-green-50 text-green-700 rounded-lg border border-green-100">{status}</div>
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
                <span className="font-medium">${Number(item.total_price).toFixed(2)}</span>
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
              <label className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-blue-50 cursor-pointer transition-colors">
                <input type="radio" name="shipping" value="standard" defaultChecked className="text-blue-600" />
                <span className="font-medium">Standard Shipping (3-5 days)</span>
              </label>
              <label className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-blue-50 cursor-pointer transition-colors">
                <input type="radio" name="shipping" value="express" className="text-blue-600" />
                <span className="font-medium">Express Shipping (1-2 days)</span>
              </label>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div data-testid="coupon-input" className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <h2 className="text-xl font-semibold mb-4">Coupon Code</h2>
            <div className="flex gap-2">
              <input type="text" placeholder="Enter code" className="flex-1 border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-600 outline-none text-gray-800" />
              <button className="bg-gray-800 text-white px-4 py-2 rounded-lg font-medium hover:bg-gray-900 transition-colors">Apply</button>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <div className="flex justify-between font-bold text-xl mb-6 text-gray-900">
              <span>Total:</span>
              <span>${Number(cart.subtotal).toFixed(2)}</span>
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
