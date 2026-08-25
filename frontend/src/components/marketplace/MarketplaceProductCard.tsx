'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Store } from 'lucide-react'
import { StarRating } from '@/components/ui/star-rating'
import { resolveI18nText } from '@/lib/i18n-text'
import { useMarketplaceCart } from '@/context/MarketplaceCartContext'
import { resolveImageUrl } from '@/lib/media'
import { isDigitalProduct } from '@/lib/stock'

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
}: {
  product: any
  lang?: string
  formatCurrency: (amount: number) => string
}) {
  const { addItem } = useMarketplaceCart()
  const [adding, setAdding] = useState(false)
  const t = STRINGS[lang as keyof typeof STRINGS] || STRINGS.en
  const name = resolveI18nText(product.name, lang)
  const image = product.primary_image_url || product.images?.[0]
  const href = `/store/${product.tenant_slug}/products/${product.slug}`

  const variant = product.variants?.[0]
  const stockKnown = Number.isFinite(variant?.stock_quantity)
  const outOfStock = !isDigitalProduct(product) && stockKnown && variant.stock_quantity <= 0

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

  return (
    <div className="group flex flex-col rounded-xl border border-border bg-card p-3 shadow-sm transition-shadow duration-300 hover:shadow-lg">
      <Link href={href} className="mb-2 block overflow-hidden rounded-lg">
        {image ? (
          // eslint-disable-next-line @next/next/no-img-element -- arbitrary vendor-supplied
          // URLs with no host allowlist, same reasoning as storefront/ProductCard.
          <img
            src={resolveImageUrl(image)}
            alt={name}
            className="aspect-square w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="aspect-square w-full bg-muted" />
        )}
      </Link>
      <span className="mb-1 inline-flex w-fit items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
        <Store className="h-3 w-3" />
        {product.tenant_name}
      </span>
      <Link
        href={href}
        className="line-clamp-2 text-sm font-semibold text-foreground transition-colors hover:text-primary"
      >
        {name}
      </Link>
      {product.review_count > 0 && (
        <div className="mt-1 flex items-center gap-1">
          <StarRating rating={product.average_rating} size={12} />
          <span className="text-xs text-muted-foreground">({product.review_count})</span>
        </div>
      )}
      <span className="mt-1 text-sm font-medium text-foreground/80">{formatCurrency(product.base_price)}</span>

      <button
        type="button"
        disabled={!variant?.id || outOfStock || adding}
        onClick={handleAddToCart}
        className="mt-3 w-full rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground transition-colors duration-150 hover:bg-primary/90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
      >
        {outOfStock ? t.outOfStock : adding ? t.adding : t.addToCart}
      </button>
    </div>
  )
}
