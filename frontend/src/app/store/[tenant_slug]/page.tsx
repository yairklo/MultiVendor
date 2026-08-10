'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { getCookie } from 'cookies-next'
import { apiClient } from '@/lib/api/apiClient'
import { useCart } from '@/context/CartContext'
import { totalStock } from '@/lib/stock'

type Lang = 'en' | 'he'

const strings: Record<Lang, { cart: string; addToCart: string; outOfStock: string; inStock: string; noProducts: string; switcherLabel: string; myOrders: string; login: string }> = {
  en: { cart: 'Cart', addToCart: 'Add to Cart', outOfStock: 'Out of stock', inStock: 'in stock', noProducts: 'No products available at the moment.', switcherLabel: 'עברית', myOrders: 'My Orders', login: 'Login' },
  he: { cart: 'עגלה', addToCart: 'הוסף לעגלה', outOfStock: 'אזל מהמלאי', inStock: 'במלאי', noProducts: 'אין מוצרים זמינים כרגע.', switcherLabel: 'English', myOrders: 'ההזמנות שלי', login: 'התחברות' },
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
  const [quantities, setQuantities] = useState<Record<number, number>>({})
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

  const getQuantity = (productId: number) => quantities[productId] ?? 1

  const setQuantity = (productId: number, qty: number, max: number) => {
    const clamped = Math.max(1, Math.min(qty, Math.max(max, 1)))
    setQuantities(prev => ({ ...prev, [productId]: clamped }))
  }

  const handleAddToCart = async (product: any) => {
    const variantId = product.variants?.[0]?.id
    if (!variantId || !tenantSlug) return
    try {
      await addItem(tenantSlug, variantId, getQuantity(product.id))
      setQuantities(prev => ({ ...prev, [product.id]: 1 }))
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

      <div className="mb-6 flex justify-end items-center gap-3">
        <Link
          data-testid="account-link"
          href={getCookie('token') ? '/account/orders' : '/login'}
          className="font-medium text-gray-600 hover:text-blue-600 transition-colors"
        >
          {getCookie('token') ? t.myOrders : t.login}
        </Link>
        <button
          data-testid="cart-icon"
          onClick={openDrawer}
          className="bg-blue-600 text-white px-4 py-2 rounded-full font-semibold shadow-md flex items-center gap-2 hover:bg-blue-700 transition-colors"
        >
          <span>{t.cart} ({cartCount})</span>
        </button>
      </div>

      <div data-testid="product-grid" className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {products.map((p, i) => {
          const stock = totalStock(p.variants)
          const stockKnown = Number.isFinite(stock)
          const outOfStock = stockKnown && stock <= 0
          const qty = getQuantity(p.id)
          return (
          <div key={i} className="bg-white border border-gray-100 p-5 rounded-xl shadow-md hover:shadow-lg transition-shadow duration-300">
            <Link href={`/store/${tenantSlug}/products/${p.slug}`} className="hover:text-blue-600 transition-colors">
              <h2 className="text-lg font-bold mb-2">{typeof p.name === 'object' ? (p.name?.[lang] || p.name?.en || p.name?.he) : p.name}</h2>
            </Link>
            <p className="text-gray-500 mb-1">${p.base_price || p.price}</p>
            {stockKnown && (
              <p className={`text-sm mb-4 ${outOfStock ? 'text-red-600 font-medium' : 'text-gray-400'}`}>
                {outOfStock ? t.outOfStock : `${stock} ${t.inStock}`}
              </p>
            )}

            {!outOfStock && (
              <div className="flex items-center gap-2 mb-3">
                <button
                  type="button"
                  aria-label="Decrease quantity"
                  onClick={() => setQuantity(p.id, qty - 1, stock)}
                  className="w-8 h-8 border rounded-lg text-gray-700 hover:bg-gray-100"
                >
                  &minus;
                </button>
                <input
                  type="number"
                  aria-label="Quantity"
                  min={1}
                  max={stockKnown ? stock : undefined}
                  value={qty}
                  onChange={e => setQuantity(p.id, Number(e.target.value) || 1, stock)}
                  className="w-12 text-center border rounded-lg py-1"
                />
                <button
                  type="button"
                  aria-label="Increase quantity"
                  onClick={() => setQuantity(p.id, qty + 1, stock)}
                  className="w-8 h-8 border rounded-lg text-gray-700 hover:bg-gray-100"
                >
                  +
                </button>
              </div>
            )}

            <button
              className="w-full mt-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-blue-600"
              onClick={() => handleAddToCart(p)}
              disabled={outOfStock}
            >
              {outOfStock ? t.outOfStock : t.addToCart}
            </button>
          </div>
          )
        })}
        {products.length === 0 && (
          <div className="col-span-full text-center py-12 text-gray-500">
            {t.noProducts}
          </div>
        )}
      </div>
    </div>
  )
}
