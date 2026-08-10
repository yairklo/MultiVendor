'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { getCookie } from 'cookies-next'
import { Search } from 'lucide-react'
import { apiClient } from '@/lib/api/apiClient'
import { useCart } from '@/context/CartContext'
import { totalStock } from '@/lib/stock'
import { StarRating } from '@/components/ui/star-rating'
import { PaginationControls, PaginationMeta } from '@/components/ui/pagination-controls'
import { ProductCardSkeleton } from '@/components/ui/skeleton'

const PAGE_SIZE = 12

type Lang = 'en' | 'he'

const strings: Record<Lang, { cart: string; addToCart: string; outOfStock: string; inStock: string; noProducts: string; switcherLabel: string; myOrders: string; login: string; searchPlaceholder: string; allCategories: string }> = {
  en: { cart: 'Cart', addToCart: 'Add to Cart', outOfStock: 'Out of stock', inStock: 'in stock', noProducts: 'No products found.', switcherLabel: 'עברית', myOrders: 'My Orders', login: 'Login', searchPlaceholder: 'Search products...', allCategories: 'All Categories' },
  he: { cart: 'עגלה', addToCart: 'הוסף לעגלה', outOfStock: 'אזל מהמלאי', inStock: 'במלאי', noProducts: 'לא נמצאו מוצרים.', switcherLabel: 'English', myOrders: 'ההזמנות שלי', login: 'התחברות', searchPlaceholder: 'חיפוש מוצרים...', allCategories: 'כל הקטגוריות' },
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
  const [productsLoading, setProductsLoading] = useState(true)
  const [meta, setMeta] = useState<PaginationMeta | null>(null)
  const [page, setPage] = useState(1)
  const [categories, setCategories] = useState<any[]>([])
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [quantities, setQuantities] = useState<Record<number, number>>({})
  const [lang, setLang] = useState<Lang>('en')
  const t = strings[lang]
  const { cart, addItem, openDrawer } = useCart()
  const cartCount = cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0

  useEffect(() => {
    const handle = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(handle)
  }, [search])

  useEffect(() => {
    if (!tenantSlug) return
    apiClient(`/api/v1/store/${tenantSlug}/categories`)
      .then(setCategories)
      .catch((e) => console.error('Failed to load categories:', e))
  }, [tenantSlug])

  // A changed search/category invalidates the current page.
  useEffect(() => {
    setPage(1)
  }, [debouncedSearch, categoryId])

  useEffect(() => {
    if (!tenantSlug) return
    setProductsLoading(true)
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) })
    if (debouncedSearch) params.set('q', debouncedSearch)
    if (categoryId) params.set('category_id', categoryId)
    apiClient(`/api/v1/store/${tenantSlug}/products?${params.toString()}`)
      .then(data => {
        // Pagination response shape: { meta, data }
        setProducts(data.data || [])
        setMeta(data.meta || null)
      })
      .catch((e) => {
        console.error("Failed to load products:", e)
        setProducts([])
        setMeta(null)
      })
      .finally(() => setProductsLoading(false))
  }, [tenantSlug, debouncedSearch, categoryId, page])

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

      <div className="mb-6 flex flex-wrap justify-between items-center gap-3">
        <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[240px]">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="search"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder={t.searchPlaceholder}
              aria-label="Search products"
              className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-200 bg-white focus:ring-2 focus:ring-blue-600 outline-none"
            />
          </div>
          {categories.length > 0 && (
            <select
              value={categoryId}
              onChange={e => setCategoryId(e.target.value)}
              aria-label="Filter by category"
              className="px-3 py-2 rounded-lg border border-gray-200 bg-white focus:ring-2 focus:ring-blue-600 outline-none"
            >
              <option value="">{t.allCategories}</option>
              {categories.map(c => (
                <option key={c.id} value={c.id}>
                  {typeof c.name === 'object' ? (c.name?.[lang] || c.name?.en || c.name?.he) : c.name}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="flex items-center gap-3">
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
      </div>

      <div data-testid="product-grid" className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {productsLoading ? (
          Array.from({ length: 8 }, (_, i) => <ProductCardSkeleton key={i} />)
        ) : products.map((p, i) => {
          const stock = totalStock(p.variants)
          const stockKnown = Number.isFinite(stock)
          const outOfStock = stockKnown && stock <= 0
          const qty = getQuantity(p.id)
          return (
          <div key={i} className="bg-white border border-gray-100 p-5 rounded-xl shadow-md hover:shadow-lg transition-shadow duration-300">
            <Link href={`/store/${tenantSlug}/products/${p.slug}`} className="hover:text-blue-600 transition-colors">
              <h2 className="text-lg font-bold mb-1">{typeof p.name === 'object' ? (p.name?.[lang] || p.name?.en || p.name?.he) : p.name}</h2>
            </Link>
            {p.review_count > 0 && (
              <div className="flex items-center gap-1.5 mb-1">
                <StarRating rating={p.average_rating} size={13} />
                <span className="text-xs text-gray-400">({p.review_count})</span>
              </div>
            )}
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
        {!productsLoading && products.length === 0 && (
          <div className="col-span-full text-center py-12 text-gray-500">
            {t.noProducts}
          </div>
        )}
      </div>

      {meta && meta.total_pages > 1 && (
        <div className="mt-6 bg-white rounded-lg shadow-sm">
          <PaginationControls meta={meta} onPageChange={setPage} />
        </div>
      )}
    </div>
  )
}
