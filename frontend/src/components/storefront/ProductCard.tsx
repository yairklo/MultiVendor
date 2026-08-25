'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useCart } from '@/context/CartContext'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'
import { totalStock } from '@/lib/stock'
import { StarRating } from '@/components/ui/star-rating'
import { resolveCardStyleClasses, CardStyle } from '@/lib/product-card-styles'

import { useCurrency } from '@/hooks/useCurrency'
import { resolveImageUrl } from '@/lib/media'
import { resolveI18nText } from '@/lib/i18n-text'

const STRINGS = {
  en: { addToCart: 'Add to Cart', outOfStock: 'Out of stock', adding: 'Adding…' },
  he: { addToCart: 'הוסף לעגלה', outOfStock: 'אזל מהמלאי', adding: 'מוסיף…' },
}

/**
 * The one place a product's Add to Cart button is ever rendered — used by the product_grid
 * section, the classic catalog listing, and the product detail page's related items. The AI
 * layout agent can only pick a `styleVariant` (product_grid.settings.card_style, clamped
 * server-side); it never emits markup for this component, so it can restyle a card's look but
 * can never touch — or remove — the real add-to-cart wiring below.
 */
export function ProductCard({
  product,
  tenantSlug,
  styleVariant = 'default',
  lang,
}: {
  product: any
  tenantSlug: string
  styleVariant?: CardStyle
  /** Defaults to the storefront's current language (see StorefrontThemeContext) when omitted --
   * callers only need to pass this explicitly to override it. */
  lang?: string
}) {
  const { addItem } = useCart()
  const { theme, lang: contextLang } = useStorefrontTheme()
  const { formatCurrency } = useCurrency()
  const [quantity, setQuantity] = useState(1)
  const [adding, setAdding] = useState(false)
  const resolvedLang = lang ?? contextLang
  const t = STRINGS[resolvedLang as keyof typeof STRINGS] || STRINGS.en
  const name = resolveI18nText(product.name, resolvedLang)

  const stock = totalStock(product.variants)
  const stockKnown = Number.isFinite(stock)
  const outOfStock = stockKnown && stock <= 0
  const image = product.primary_image_url || product.images?.[0]

  const handleAddToCart = async () => {
    const variantId = product.variants?.[0]?.id
    if (!variantId) return
    setAdding(true)
    try {
      await addItem(tenantSlug, variantId, quantity)
      setQuantity(1)
    } catch {
      // CartContext surfaces its own errors; nothing further to do here.
    } finally {
      setAdding(false)
    }
  }

  return (
    <div className={`group flex flex-col p-3 active:scale-[0.98] transition-transform duration-100 ease-spring ${resolveCardStyleClasses(styleVariant)}`}>
      <Link href={`/store/${tenantSlug}/products/${product.slug}`} className="mb-2 block overflow-hidden rounded-lg">
        {image ? (
          // eslint-disable-next-line @next/next/no-img-element -- arbitrary vendor-supplied
          // URLs with no host allowlist; next/image would require allowing every hostname,
          // turning the server into an open image proxy (see next.config.ts history).
          <img
            src={resolveImageUrl(image)}
            alt={name}
            className="aspect-square w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="aspect-square w-full bg-gray-100" />
        )}
      </Link>
      <Link
        href={`/store/${tenantSlug}/products/${product.slug}`}
        className="line-clamp-2 text-sm font-semibold tracking-tight text-balance text-gray-900 transition-colors hover:text-blue-600"
      >
        {name}
      </Link>
      {product.review_count > 0 && (
        <div className="mt-1 flex items-center gap-1">
          <StarRating rating={product.average_rating} size={12} />
          <span className="text-xs text-gray-400 tabular-nums">({product.review_count})</span>
        </div>
      )}
      <span className="mt-1 text-sm font-medium tabular-nums text-gray-700">{formatCurrency(product.base_price ?? product.price)}</span>

      <button
        type="button"
        disabled={outOfStock || adding}
        onClick={handleAddToCart}
        className={`mt-3 w-full px-3 py-2 text-xs font-semibold active:scale-[0.98] transition-all duration-100 ease-spring disabled:cursor-not-allowed disabled:opacity-50 ${theme.primaryButtonClass}`}
      >
        {outOfStock ? t.outOfStock : adding ? t.adding : t.addToCart}
      </button>
    </div>
  )
}
