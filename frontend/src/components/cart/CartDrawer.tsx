'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import { useCart } from '@/context/CartContext'

export function CartDrawer() {
  const { cart, isOpen, closeDrawer, incrementItem, decrementItem, removeItem } = useCart()
  const router = useRouter()

  if (!isOpen) return null

  const handleCheckout = () => {
    closeDrawer()
    router.push('/checkout')
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/40" onClick={closeDrawer} />
      <div data-testid="cart-drawer" className="relative w-full max-w-md h-full bg-white shadow-xl flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-bold text-gray-900">Your Cart</h2>
          <button
            aria-label="Close cart"
            onClick={closeDrawer}
            className="text-gray-500 hover:text-gray-800 text-2xl leading-none"
          >
            &times;
          </button>
        </div>

        <div className="flex-1 overflow-auto p-4 space-y-4">
          {(!cart || cart.items.length === 0) && (
            <p className="text-gray-500 text-center py-8">Your cart is empty.</p>
          )}
          {cart?.items.map(item => (
            <div key={item.id} data-testid="cart-item" className="flex gap-3 border-b pb-4">
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
                <div className="text-gray-500">${Number(item.unit_price).toFixed(2)}</div>
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
              <div className="font-semibold text-gray-900">${Number(item.total_price).toFixed(2)}</div>
            </div>
          ))}
        </div>

        {cart && cart.items.length > 0 && (
          <div className="p-4 border-t space-y-3">
            <div className="flex justify-between font-bold text-lg text-gray-900">
              <span>Subtotal</span>
              <span data-testid="cart-subtotal">${Number(cart.subtotal).toFixed(2)}</span>
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
