'use client'

import React, { useState } from 'react'
import { apiClient } from '@/lib/api/apiClient'

export default function CheckoutPage() {
  const [status, setStatus] = useState<string>('')

  const handleCheckout = async () => {
    try {
      await apiClient('/api/v1/cart/checkout', {
        method: 'POST',
        body: JSON.stringify({ items: [], shipping: 'standard', coupon: '' })
      })
      setStatus('Order placed successfully!')
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-gray-50 min-h-screen">
      <h1 className="text-3xl font-bold mb-8 text-gray-900 border-b pb-4">Checkout</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2 space-y-6">
          <div data-testid="item-summary" className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <h2 className="text-xl font-semibold mb-4">Item Summary</h2>
            <div className="flex justify-between items-center py-2 border-b text-gray-700">
              <span>Premium Product</span>
              <span className="font-medium">$99.00</span>
            </div>
          </div>

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
              <span>$99.00</span>
            </div>
            <button 
              onClick={handleCheckout}
              className="w-full bg-blue-600 text-white py-3 rounded-xl font-bold text-lg hover:bg-blue-700 shadow-lg hover:shadow-xl active:scale-[0.98] transition-all"
            >
              Place Order
            </button>
            {status && <div className="mt-4 text-green-600 font-semibold text-center">{status}</div>}
          </div>
        </div>
      </div>
    </div>
  )
}
