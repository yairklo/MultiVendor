'use client'

import React, { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api/apiClient'
import { useCart } from '@/context/CartContext'

type Lang = 'en' | 'he'

const strings: Record<Lang, { cart: string; addToCart: string; noProducts: string; switcherLabel: string }> = {
  en: { cart: 'Cart', addToCart: 'Add to Cart', noProducts: 'No products available at the moment.', switcherLabel: 'עברית' },
  he: { cart: 'עגלה', addToCart: 'הוסף לעגלה', noProducts: 'אין מוצרים זמינים כרגע.', switcherLabel: 'English' },
}

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
  const [lang, setLang] = useState<Lang>('en')
  const t = strings[lang]
  const { cart, addItem, openDrawer } = useCart()
  const cartCount = cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0
  
  useEffect(() => {
    if (!tenantSlug) return
    apiClient(`/api/v1/store/${tenantSlug}/products`)
      .then(data => {
        // Pagination response shape: { meta, data }
        setProducts(data.data || [])
      })
      .catch((e) => {
        console.error("Failed to load products:", e)
        setProducts([])
      })
  }, [tenantSlug])

  const handleAddToCart = async (product: any) => {
    const variantId = product.variants?.[0]?.id
    if (!variantId || !tenantSlug) return
    try {
      await addItem(tenantSlug, variantId, 1)
    } catch (e) {
      console.error('Failed to add item to cart:', e)
    }
  }

  if (!tenantSlug) return <div>Loading...</div>

  return (
    <div dir={lang === 'he' ? 'rtl' : 'ltr'} className="p-4 bg-gray-50 min-h-screen text-gray-900">
      <header className="flex justify-between items-center mb-8 bg-white p-4 shadow-sm rounded-lg">
        <div data-testid="tenant-logo" className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
          Logo
        </div>
        <button
          data-testid="language-switcher"
          className="cursor-pointer font-medium hover:text-blue-600 transition-colors"
          onClick={() => setLang(l => (l === 'en' ? 'he' : 'en'))}
        >
          {t.switcherLabel}
        </button>
      </header>

      <div className="mb-6 flex justify-end">
        <button
          data-testid="cart-icon"
          onClick={openDrawer}
          className="bg-blue-600 text-white px-4 py-2 rounded-full font-semibold shadow-md flex items-center gap-2 hover:bg-blue-700 transition-colors"
        >
          <span>{t.cart} ({cartCount})</span>
        </button>
      </div>

      <div data-testid="product-grid" className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {products.map((p, i) => (
          <div key={i} className="bg-white border border-gray-100 p-5 rounded-xl shadow-md hover:shadow-lg transition-shadow duration-300">
            <h2 className="text-lg font-bold mb-2">{typeof p.name === 'object' ? (p.name?.[lang] || p.name?.en || p.name?.he) : p.name}</h2>
            <p className="text-gray-500 mb-4">${p.base_price || p.price}</p>
            <button
              className="w-full mt-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 active:scale-95 transition-all"
              onClick={() => handleAddToCart(p)}
            >
              {t.addToCart}
            </button>
          </div>
        ))}
        {products.length === 0 && (
          <div className="col-span-full text-center py-12 text-gray-500">
            {t.noProducts}
          </div>
        )}
      </div>
    </div>
  )
}
