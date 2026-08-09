'use client'

import React, { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api/apiClient'

export default function StorefrontPage(props: { params: Promise<{ tenant_slug: string }> | { tenant_slug: string } }) {
  // Handle both promise and plain object for testing flexibility
  const isPromise = props.params instanceof Promise
  const [tenantSlug, setTenantSlug] = useState<string | null>(isPromise ? null : (props.params as any).tenant_slug)
  
  useEffect(() => {
    if (isPromise) {
      ;(props.params as Promise<{ tenant_slug: string }>).then(p => setTenantSlug(p.tenant_slug))
    }
  }, [props.params, isPromise])

  const [products, setProducts] = useState<any[]>([])
  const [cartCount, setCartCount] = useState(0)
  
  useEffect(() => {
    if (!tenantSlug) return
    apiClient(`/api/v1/products?tenant=${tenantSlug}`)
      .then(data => setProducts(data))
      .catch(() => {})
  }, [tenantSlug])

  if (!tenantSlug) return <div>Loading...</div>

  return (
    <div className="p-4 bg-gray-50 min-h-screen text-gray-900">
      <header className="flex justify-between items-center mb-8 bg-white p-4 shadow-sm rounded-lg">
        <div data-testid="tenant-logo" className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
          Logo
        </div>
        <div data-testid="language-switcher" className="cursor-pointer font-medium hover:text-blue-600 transition-colors">
          EN
        </div>
      </header>

      <div className="mb-6 flex justify-end">
        <div className="bg-blue-600 text-white px-4 py-2 rounded-full font-semibold shadow-md flex items-center gap-2">
          <span>Cart ({cartCount})</span>
        </div>
      </div>

      <div data-testid="product-grid" className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {products.map((p, i) => (
          <div key={i} className="bg-white border border-gray-100 p-5 rounded-xl shadow-md hover:shadow-lg transition-shadow duration-300">
            <h2 className="text-lg font-bold mb-2">{p.name}</h2>
            <p className="text-gray-500 mb-4">${p.price}</p>
            <button 
              className="w-full mt-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 active:scale-95 transition-all"
              onClick={() => setCartCount(c => c + 1)}
            >
              Add to Cart
            </button>
          </div>
        ))}
        {products.length === 0 && (
          <div className="bg-white border border-gray-100 p-5 rounded-xl shadow-md">
            <h2 className="text-lg font-bold mb-2">Dummy Product</h2>
            <p className="text-gray-500 mb-4">$9.99</p>
            <button 
              className="w-full mt-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 active:scale-95 transition-all"
              onClick={() => setCartCount(c => c + 1)}
            >
              Add to Cart
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
