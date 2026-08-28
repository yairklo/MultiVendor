'use client'

import { CSSProperties, useEffect, useState } from 'react'
import { Section } from '@/lib/ai/types'
import { apiClient } from '@/lib/api/apiClient'
import { ProductCard } from '../ProductCard'
import { CardStyle } from '@/lib/product-card-styles'
import { resolveI18nText } from '@/lib/i18n-text'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'
import { isUsableTenantSlug } from '@/lib/tenantSlug'
import type { Product } from '@/lib/types'

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
  const { lang } = useStorefrontTheme()
  const columns = Number(section.settings.columns ?? 4)
  const categoryId = section.settings.category_id
  const cardStyle: CardStyle = typeof section.settings.card_style === 'string' ? (section.settings.card_style as CardStyle) : 'default'
  const [products, setProducts] = useState<Product[] | null>(null)
  const tenantUsable = isUsableTenantSlug(tenantSlug)

  useEffect(() => {
    if (!tenantUsable) return
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
  }, [tenantUsable, tenantSlug, categoryId, columns])

  return (
    <div
      className="rounded-2xl p-6"
      style={{ ...themeStyle, background: 'var(--section-bg, #f9fafb)', color: 'var(--section-text, #111827)' }}
    >
      <h2 className="mb-4 text-xl font-bold">{resolveI18nText(section.settings.title, lang) || 'Products'}</h2>
      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
        {products === null &&
          Array.from({ length: columns * 2 }).map((_, i) => (
            <div key={i} className="animate-pulse rounded-xl border border-gray-100 bg-white p-3 shadow-sm">
              <div className="mb-2 aspect-square rounded-lg bg-gray-100" />
              <span className="text-sm text-gray-600">Product {i + 1}</span>
            </div>
          ))}

        {products !== null && products.length === 0 && (
          <div className="col-span-full text-sm text-gray-400">No products in this collection yet.</div>
        )}

        {products !== null &&
          tenantSlug &&
          products.map((p) => (
            <ProductCard key={p.id} product={p} tenantSlug={tenantSlug} styleVariant={cardStyle} />
          ))}
      </div>
      {typeof section.settings.collection === 'string' && section.settings.collection && !categoryId && (
        <div className="mt-3 text-xs text-current/60">collection: {section.settings.collection}</div>
      )}
    </div>
  )
}
