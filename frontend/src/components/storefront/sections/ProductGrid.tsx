'use client'

import { CSSProperties, useEffect, useState } from 'react'
import Link from 'next/link'
import { Section } from '@/lib/ai/types'
import { apiClient } from '@/lib/api/apiClient'
import { useCart } from '@/context/CartContext'
import { totalStock } from '@/lib/stock'
import { StarRating } from '@/components/ui/star-rating'

function productName(p: any): string {
  return typeof p.name === 'object' ? p.name?.en || p.name?.he || Object.values(p.name ?? {})[0] || '' : p.name
}

export function ProductGrid({
  section,
  themeStyle,
  tenantSlug,
}: {
  section: Section
  themeStyle: CSSProperties
  /** When provided, fetches and renders real products for this store instead of placeholders. */
  tenantSlug?: string
}) {
  const columns = Number(section.settings.columns ?? 4)
  const categoryId = section.settings.category_id
  const [products, setProducts] = useState<any[] | null>(null)
  const [quantities, setQuantities] = useState<Record<number, number>>({})
  const { addItem } = useCart()

  useEffect(() => {
    if (!tenantSlug) {
      setProducts(null)
      return
    }
    let cancelled = false
    const params = new URLSearchParams({ page: '1', page_size: String(columns * 2) })
    if (categoryId) params.set('category_id', String(categoryId))
    apiClient(`/api/v1/store/${tenantSlug}/products?${params.toString()}`)
      .then((data) => {
        if (!cancelled) setProducts(data.data || [])
      })
      .catch(() => {
        if (!cancelled) setProducts([])
      })
    return () => {
      cancelled = true
    }
  }, [tenantSlug, categoryId, columns])

  const getQuantity = (id: number) => quantities[id] ?? 1

  async function handleAddToCart(p: any) {
    const variantId = p.variants?.[0]?.id
    if (!variantId || !tenantSlug) return
    try {
      await addItem(tenantSlug, variantId, getQuantity(p.id))
      setQuantities((prev) => ({ ...prev, [p.id]: 1 }))
    } catch {
      // CartContext surfaces its own errors; nothing further to do here.
    }
  }

  return (
    <div
      className="rounded-2xl p-6"
      style={{ ...themeStyle, background: 'var(--section-bg, #f9fafb)', color: 'var(--section-text, #111827)' }}
    >
      <h2 className="mb-4 text-xl font-bold">{section.settings.title ?? 'Products'}</h2>
      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
        {products === null &&
          Array.from({ length: columns * 2 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-gray-100 bg-white p-3 shadow-sm">
              <div className="mb-2 aspect-square rounded-lg bg-gray-100" />
              <span className="text-sm text-gray-600">Product {i + 1}</span>
            </div>
          ))}

        {products !== null && products.length === 0 && (
          <div className="col-span-full text-sm text-gray-400">No products in this collection yet.</div>
        )}

        {products !== null &&
          products.map((p) => {
            const stock = totalStock(p.variants)
            const stockKnown = Number.isFinite(stock)
            const outOfStock = stockKnown && stock <= 0
            return (
              <div key={p.id} className="flex flex-col rounded-xl border border-gray-100 bg-white p-3 shadow-sm">
                <Link href={`/store/${tenantSlug}/products/${p.slug}`} className="mb-2 hover:text-blue-600">
                  <div className="mb-2 aspect-square rounded-lg bg-gray-100" />
                  <span className="text-sm font-semibold text-gray-900">{productName(p)}</span>
                </Link>
                {p.review_count > 0 && (
                  <div className="mb-1 flex items-center gap-1">
                    <StarRating rating={p.average_rating} size={12} />
                    <span className="text-xs text-gray-400">({p.review_count})</span>
                  </div>
                )}
                <span className="mb-2 text-sm text-gray-500">${p.base_price ?? p.price}</span>
                <button
                  type="button"
                  disabled={outOfStock}
                  onClick={() => handleAddToCart(p)}
                  className="mt-auto rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {outOfStock ? 'Out of stock' : 'Add to Cart'}
                </button>
              </div>
            )
          })}
      </div>
      {section.settings.collection && !categoryId && (
        <div className="mt-3 text-xs text-current/60">collection: {section.settings.collection}</div>
      )}
    </div>
  )
}
