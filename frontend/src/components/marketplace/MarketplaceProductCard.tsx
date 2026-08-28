'use client'

import { useState } from 'react'
import Link from 'next/link'
import { StarRating } from '@/components/ui/star-rating'
import { resolveI18nText } from '@/lib/i18n-text'
import { useMarketplaceCart } from '@/context/MarketplaceCartContext'
import { resolveImageUrl } from '@/lib/media'
import { isDigitalProduct } from '@/lib/stock'
import { cn } from '@/lib/utils'
import type { MarketplaceProduct } from '@/lib/types'

const STRINGS = {
  en: { addToCart: 'Add to Cart', outOfStock: 'Out of stock', adding: 'Adding…' },
  he: { addToCart: 'הוסף לעגלה', outOfStock: 'אזל מהמלאי', adding: 'מוסיף…' },
}

/**
 * Cross-store equivalent of storefront/ProductCard: same one-click-first-variant
 * Add to Cart convention, but adds to the marketplace cart (MarketplaceCartContext)
 * instead of a single store's cart, since a purchase from here can span vendors.
 * Image/title still link through to the vendor's own product page for anyone who
 * wants full details (variant options, reviews, description) before buying.
 */
export function MarketplaceProductCard({
  product,
  lang = 'he',
  formatCurrency,
  featured = false,
}: {
  product: MarketplaceProduct
  lang?: string
  formatCurrency: (amount: number) => string
  featured?: boolean
}) {
  const { addItem } = useMarketplaceCart()
  const [adding, setAdding] = useState(false)
  const t = STRINGS[lang as keyof typeof STRINGS] || STRINGS.en
  const name = resolveI18nText(product.name, lang)
  const image = product.primary_image_url || product.images?.[0]
  const href = `/store/${product.tenant_slug}/products/${product.slug}`

  const variant = product.variants?.[0]
  const stockKnown = Number.isFinite(variant?.stock_quantity)
  const outOfStock = !isDigitalProduct(product) && stockKnown && variant!.stock_quantity <= 0

  const handleAddToCart = async () => {
    if (!variant?.id) return
    setAdding(true)
    try {
      await addItem(variant.id, 1)
    } catch {
      // MarketplaceCartContext surfaces its own errors; nothing further to do here.
    } finally {
      setAdding(false)
    }
  }

  const addButton = (
    <button
      type="button"
      disabled={!variant?.id || outOfStock || adding}
      onClick={handleAddToCart}
      className="self-start border-b border-foreground pb-0.5 text-sm font-medium text-foreground transition-opacity hover:opacity-60 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40 motion-safe:transition-transform"
    >
      {outOfStock ? t.outOfStock : adding ? t.adding : t.addToCart}
    </button>
  )

  if (featured) {
    return (
      <article className="group grid items-end gap-8 border-b border-border pb-12 md:grid-cols-2 md:gap-12">
        <Link href={href} className="block overflow-hidden bg-muted">
          {image ? (
            // Arbitrary vendor-supplied URLs with no host allowlist, same reasoning
            // as storefront/ProductCard.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={resolveImageUrl(image)}
              alt={name}
              className="aspect-[4/5] w-full object-cover motion-safe:transition-transform motion-safe:duration-700 motion-safe:ease-spring motion-safe:group-hover:scale-[1.03]"
            />
          ) : (
            <div className="aspect-[4/5] w-full bg-muted" />
          )}
        </Link>
        <div className="flex flex-col gap-4 pb-2">
          <p className="text-[11px] font-medium uppercase tracking-[0.22em] text-muted-foreground">
            {product.tenant_name}
          </p>
          <Link
            href={href}
            className="font-heading text-4xl font-medium leading-[1.12] text-foreground md:text-5xl"
          >
            {name}
          </Link>
          {product.review_count > 0 && (
            <div className="flex items-center gap-1">
              <StarRating rating={product.average_rating ?? 0} size={14} />
              <span className="text-xs tabular-nums text-muted-foreground">({product.review_count})</span>
            </div>
          )}
          <span className="font-heading text-2xl tabular-nums text-foreground">
            {formatCurrency(product.base_price)}
          </span>
          {addButton}
        </div>
      </article>
    )
  }

  return (
    <article className="group flex flex-col">
      <Link href={href} className="mb-3 block overflow-hidden bg-muted">
        {image ? (
          // Arbitrary vendor-supplied URLs with no host allowlist, same reasoning
          // as storefront/ProductCard.
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
      <p className="mb-1 text-[10px] font-medium uppercase tracking-[0.2em] text-muted-foreground">
        {product.tenant_name}
      </p>
      <Link
        href={href}
        className={cn(
          'line-clamp-2 font-heading text-lg font-medium leading-snug text-foreground transition-opacity hover:opacity-70',
        )}
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
      <div className="mt-3">{addButton}</div>
    </article>
  )
}
