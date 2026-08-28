'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useCart } from '@/context/CartContext'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'
import { totalStock, isDigitalProduct } from '@/lib/stock'
import { StarRating } from '@/components/ui/star-rating'
import { resolveCardStyleClasses, CardStyle } from '@/lib/product-card-styles'

import { useCurrency } from '@/hooks/useCurrency'
import { resolveImageUrl } from '@/lib/media'
import { resolveI18nText } from '@/lib/i18n-text'
import type { Product } from '@/lib/types'

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
  product: Product
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
  const outOfStock = !isDigitalProduct(product) && stockKnown && stock <= 0
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
    <div className={`group flex flex-col ${resolveCardStyleClasses(styleVariant)}`}>
      <Link href={`/store/${tenantSlug}/products/${product.slug}`} className="mb-3 block overflow-hidden">
        {image ? (
          // Arbitrary vendor-supplied URLs with no host allowlist; next/image would
          // require allowing every hostname, turning the server into an open image
          // proxy (see next.config.ts history).
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={resolveImageUrl(image)}
            alt={name}
            className="aspect-[4/5] w-full object-cover motion-safe:transition-transform motion-safe:duration-500 motion-safe:group-hover:scale-[1.04]"
          />
        ) : (
          <div className="aspect-[4/5] w-full bg-muted" />
        )}
      </Link>
      <Link
        href={`/store/${tenantSlug}/products/${product.slug}`}
        className="line-clamp-2 font-heading text-lg font-medium leading-snug text-foreground transition-opacity hover:opacity-70"
      >
        {name}
      </Link>
      {product.review_count > 0 && (
        <div className="mt-1 flex items-center gap-1">
          <StarRating rating={product.average_rating ?? 0} size={12} />
          <span className="text-xs tabular-nums text-muted-foreground">({product.review_count})</span>
        </div>
      )}
      <span className="mt-2 text-sm tabular-nums text-foreground">{formatCurrency(product.base_price)}</span>

      <button
        type="button"
        disabled={outOfStock || adding}
        onClick={handleAddToCart}
        className={`mt-3 w-full px-3 py-2 text-xs font-semibold motion-safe:active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 ${theme.primaryButtonClass}`}
      >
        {outOfStock ? t.outOfStock : adding ? t.adding : t.addToCart}
      </button>
    </div>
  )
}
