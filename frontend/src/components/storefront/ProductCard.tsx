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

import { cn } from '@/lib/utils'

const STRINGS = {
  en: { addToCart: 'Add to Cart', outOfStock: 'Out of stock', adding: 'Adding…' },
  he: { addToCart: 'הוסף לעגלה', outOfStock: 'אזל מהמלאי', adding: 'מוסיף…' },
}

/**
 * The one place a product's Add to Cart button is ever rendered — used by the product_grid
 * section, the classic catalog listing, and the product detail page's related items. Matches
 * the editorial, minimalist design of MarketplaceProductCard.
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
  const { lang: contextLang } = useStorefrontTheme()
  const { formatCurrency } = useCurrency()
  const [quantity, setQuantity] = useState(1)
  const [adding, setAdding] = useState(false)
  const resolvedLang = lang ?? contextLang
  const t = STRINGS[resolvedLang as keyof typeof STRINGS] || STRINGS.en
  const name = resolveI18nText(product.name, resolvedLang)

  const variant = product.variants?.[0]
  const variantId = variant?.id
  const stock = totalStock(product.variants)
  const stockKnown = Number.isFinite(stock)
  const outOfStock = !isDigitalProduct(product) && stockKnown && stock <= 0
  const image = product.primary_image_url || product.images?.[0]

  const handleAddToCart = async () => {
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

  const href = `/store/${tenantSlug}/products/${product.slug}`

  return (
    <article className={cn('group flex flex-col', resolveCardStyleClasses(styleVariant))}>
      <Link href={href} className="mb-3 block overflow-hidden bg-muted">
        {image ? (
          // Arbitrary vendor-supplied URLs with no host allowlist; next/image would
          // require allowing every hostname, turning the server into an open image
          // proxy (see next.config.ts history).
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={resolveImageUrl(image)}
            alt={name}
            className="aspect-[4/5] w-full object-cover motion-safe:transition-transform motion-safe:duration-500 motion-safe:ease-spring motion-safe:group-hover:scale-[1.04]"
          />
        ) : (
          <div className="aspect-[4/5] w-full bg-muted" />
        )}
      </Link>
      <Link
        href={href}
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

      <div className="mt-3">
        <button
          type="button"
          disabled={!variantId || outOfStock || adding}
          onClick={handleAddToCart}
          className="self-start border-b border-foreground pb-0.5 text-sm font-medium text-foreground transition-opacity hover:opacity-60 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40 motion-safe:transition-transform"
        >
          {outOfStock ? t.outOfStock : adding ? t.adding : t.addToCart}
        </button>
      </div>
    </article>
  )
}
