'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { getCookie } from 'cookies-next'
import { apiClient, ApiError } from '@/lib/api/apiClient'
import { useCart } from '@/context/CartContext'
import { useMarketplaceCartSafe } from '@/context/MarketplaceCartContext'
import { useToast } from '@/context/ToastContext'
import { totalStock, isDigitalProduct } from '@/lib/stock'
import { StarRating } from '@/components/ui/star-rating'
import { Star } from 'lucide-react'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'
import { useCurrency } from '@/hooks/useCurrency'
import { resolveImageUrl } from '@/lib/media'
import { resolveI18nText } from '@/lib/i18n-text'
import { formatUiDate } from '@/lib/utils'
import { errorMessage } from '@/lib/errors'
import type { Product, ProductReview } from '@/lib/types'

const STRINGS = {
  en: {
    backToStore: '← Back to store',
    backToMarketplace: '← Back to marketplace',
    soldBy: 'Sold by',
    noImage: 'No image',
    outOfStock: 'Out of stock',
    inStock: (n: number) => `${n} in stock`,
    digitalDelivery: 'Digital product — delivered instantly, no shipping.',
    decreaseQuantity: 'Decrease quantity',
    increaseQuantity: 'Increase quantity',
    quantity: 'Quantity',
    adding: 'Adding...',
    addToCart: 'Add to Cart',
    reviews: 'Reviews',
    rateStars: (n: number) => `Rate ${n} stars`,
    sharePlaceholder: 'Share your thoughts about this product...',
    submitting: 'Submitting...',
    submitReview: 'Submit Review',
    signIn: 'Sign in',
    signInToReview: 'to write a review.',
    noReviewsYet: 'No reviews yet.',
    verifiedPurchase: 'Verified Purchase',
    reviewWord: (n: number) => (n === 1 ? 'review' : 'reviews'),
    thanksForReview: 'Thanks for your review!',
    alreadyReviewed: "You've already reviewed this product.",
    failedToSubmitReview: 'Failed to submit review',
  },
  he: {
    backToStore: '→ חזרה לחנות',
    backToMarketplace: '→ חזרה למרקטפלייס',
    soldBy: 'נמכר ע״י',
    noImage: 'אין תמונה',
    outOfStock: 'אזל מהמלאי',
    inStock: (n: number) => `${n} במלאי`,
    digitalDelivery: 'מוצר דיגיטלי — מסופק מיד, בלי משלוח.',
    decreaseQuantity: 'הקטנת כמות',
    increaseQuantity: 'הגדלת כמות',
    quantity: 'כמות',
    adding: 'מוסיף…',
    addToCart: 'הוסף לעגלה',
    reviews: 'ביקורות',
    rateStars: (n: number) => `דירוג ${n} כוכבים`,
    sharePlaceholder: 'שתפו את דעתכם על המוצר...',
    submitting: 'שולח…',
    submitReview: 'שליחת ביקורת',
    signIn: 'התחברות',
    signInToReview: 'כדי לכתוב ביקורת.',
    noReviewsYet: 'אין עדיין ביקורות.',
    verifiedPurchase: 'רכישה מאומתת',
    reviewWord: (n: number) => (n === 1 ? 'ביקורת' : 'ביקורות'),
    thanksForReview: 'תודה על הביקורת!',
    alreadyReviewed: 'כבר כתבתם ביקורת על המוצר הזה.',
    failedToSubmitReview: 'שליחת הביקורת נכשלה',
  },
}

export function ProductDetailView({
  tenantSlug,
  slug,
  product,
  initialReviews,
  mode = 'store',
  storeName,
}: {
  tenantSlug: string
  slug: string
  product: Product
  initialReviews: ProductReview[]
  mode?: 'store' | 'marketplace'
  storeName?: string
}) {
  const [quantity, setQuantity] = useState(1)
  const [adding, setAdding] = useState(false)
  const [reviews, setReviews] = useState<ProductReview[]>(initialReviews)
  const [reviewRating, setReviewRating] = useState(5)
  const [reviewComment, setReviewComment] = useState('')
  const [submittingReview, setSubmittingReview] = useState(false)
  const singleStoreCart = useCart()
  const marketplaceCart = useMarketplaceCartSafe()
  const { showToast } = useToast()
  const { theme, lang } = useStorefrontTheme()
  const { formatCurrency } = useCurrency()
  const t = STRINGS[lang as keyof typeof STRINGS] || STRINGS.en

  const loadReviews = () => {
    apiClient(`/api/v1/store/${tenantSlug}/products/${slug}/reviews`)
      .then(setReviews)
      .catch((e) => console.error('Failed to load reviews:', e))
  }

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmittingReview(true)
    try {
      await apiClient(`/api/v1/store/${tenantSlug}/reviews`, {
        method: 'POST',
        body: JSON.stringify({ product_id: product.id, rating: reviewRating, comment: reviewComment || undefined }),
      })
      showToast(t.thanksForReview, 'success')
      setReviewComment('')
      setReviewRating(5)
      loadReviews()
    } catch (e) {
      if (e instanceof ApiError && e.status === 400) {
        showToast(t.alreadyReviewed, 'error')
      } else {
        showToast(errorMessage(e) || t.failedToSubmitReview, 'error')
      }
    } finally {
      setSubmittingReview(false)
    }
  }

  const stock = totalStock(product.variants)
  const digital = isDigitalProduct(product)
  const stockKnown = !digital && Number.isFinite(stock)
  const outOfStock = stockKnown && stock <= 0
  const name = resolveI18nText(product.name, lang)
  const description = resolveI18nText(product.description, lang)
  const images: string[] = product.images?.length ? product.images : (product.primary_image_url ? [product.primary_image_url] : [])

  const [selectedImageIdx, setSelectedImageIdx] = useState(0)

  const clampQuantity = (qty: number) => Math.max(1, Math.min(qty, stockKnown ? Math.max(stock, 1) : qty))

  const handleAddToCart = async () => {
    const variantId = product.variants?.[0]?.id
    if (!variantId) return
    setAdding(true)
    try {
      if (mode === 'marketplace') {
        if (marketplaceCart) {
          await marketplaceCart.addItem(variantId, quantity)
          marketplaceCart.openDrawer()
        }
      } else {
        await singleStoreCart.addItem(tenantSlug, variantId, quantity)
        singleStoreCart.openDrawer()
      }
    } catch (e) {
      console.error('Failed to add item to cart:', e)
    } finally {
      setAdding(false)
    }
  }

  const activeImage = images[selectedImageIdx] || images[0]

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 md:px-8 md:py-12 text-foreground">
      {mode === 'marketplace' ? (
        <div className="flex items-center justify-between gap-4 mb-8">
          <Link
            href="/marketplace"
            className="inline-flex items-center gap-1.5 text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground transition-colors hover:text-foreground"
          >
            {t.backToMarketplace}
          </Link>
          <Link
            href={`/store/${tenantSlug}`}
            className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground transition-colors hover:text-foreground hover:underline"
          >
            {t.soldBy}: <span className="font-semibold text-foreground">{storeName || tenantSlug}</span>
          </Link>
        </div>
      ) : (
        <Link
          href={`/store/${tenantSlug}`}
          className="inline-flex items-center gap-1.5 text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground transition-colors hover:text-foreground mb-8"
        >
          {t.backToStore}
        </Link>
      )}

      <div className="grid grid-cols-1 gap-10 md:grid-cols-2 md:gap-14 lg:gap-16 items-start">
        {/* Product Images Column */}
        <div className="flex flex-col gap-3">
          <div className="aspect-[4/5] w-full overflow-hidden bg-muted rounded-md border border-border/40 relative">
            {activeImage ? (
              // Arbitrary vendor-supplied URLs with no host allowlist
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={resolveImageUrl(activeImage)}
                alt={name}
                className="h-full w-full object-cover motion-safe:transition-transform motion-safe:duration-500"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-sm text-muted-foreground">
                {t.noImage}
              </div>
            )}
          </div>

          {images.length > 1 && (
            <div className="flex items-center gap-3 overflow-x-auto pb-1 pt-1">
              {images.map((img, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setSelectedImageIdx(idx)}
                  className={`relative aspect-[4/5] w-20 flex-shrink-0 overflow-hidden rounded-md border-2 transition-all ${
                    idx === selectedImageIdx
                      ? 'border-foreground opacity-100 shadow-sm'
                      : 'border-transparent opacity-60 hover:opacity-100'
                  }`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={resolveImageUrl(img)} alt="" className="h-full w-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Product Info Column */}
        <div className="flex flex-col">
          <h1 className={`text-3xl font-medium tracking-tight md:text-4xl lg:text-5xl leading-[1.15] text-foreground ${theme.headingFont}`}>
            {name}
          </h1>

          {product.review_count > 0 && (
            <a
              href="#reviews"
              className="mt-3 inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <StarRating rating={product.average_rating ?? 0} size={14} />
              <span className="tabular-nums">
                ({product.review_count} {t.reviewWord(product.review_count)})
              </span>
            </a>
          )}

          <div className="mt-4 text-2xl font-medium tabular-nums text-foreground md:text-3xl">
            {formatCurrency(product.base_price)}
          </div>

          <div className="mt-4 border-t border-border/60 pt-4">
            {digital ? (
              <p className="inline-block rounded-md border border-border/80 bg-muted/40 px-3 py-1.5 text-xs text-muted-foreground">
                {t.digitalDelivery}
              </p>
            ) : stockKnown && (
              <div className="flex items-center gap-2 text-xs font-medium">
                <span className={`h-2 w-2 rounded-full ${outOfStock ? 'bg-destructive' : 'bg-emerald-500'}`} />
                <span className={outOfStock ? 'text-destructive font-semibold' : 'text-muted-foreground'}>
                  {outOfStock ? t.outOfStock : t.inStock(stock)}
                </span>
              </div>
            )}
          </div>

          {description && (
            <div className="mt-6 text-sm leading-relaxed text-muted-foreground md:text-base whitespace-pre-line">
              {description}
            </div>
          )}

          <div className="mt-8 flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
            {!outOfStock && (
              <div className="inline-flex h-12 items-center rounded-lg border border-input bg-background self-start">
                <button
                  type="button"
                  aria-label={t.decreaseQuantity}
                  onClick={() => setQuantity(q => clampQuantity(q - 1))}
                  className="px-3.5 h-full text-foreground/70 transition-colors hover:text-foreground active:scale-95 text-base"
                >
                  &minus;
                </button>
                <input
                  type="number"
                  aria-label={t.quantity}
                  min={1}
                  max={stockKnown ? stock : undefined}
                  value={quantity}
                  onChange={e => setQuantity(clampQuantity(Number(e.target.value) || 1))}
                  className="w-12 text-center text-sm font-semibold outline-none bg-transparent tabular-nums"
                />
                <button
                  type="button"
                  aria-label={t.increaseQuantity}
                  onClick={() => setQuantity(q => clampQuantity(q + 1))}
                  className="px-3.5 h-full text-foreground/70 transition-colors hover:text-foreground active:scale-95 text-base"
                >
                  +
                </button>
              </div>
            )}

            <button
              onClick={handleAddToCart}
              disabled={outOfStock || adding}
              className={`h-12 flex-1 px-8 text-sm font-semibold transition-all duration-150 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed rounded-lg ${theme.primaryButtonClass}`}
            >
              {outOfStock ? t.outOfStock : adding ? t.adding : t.addToCart}
            </button>
          </div>
        </div>
      </div>

      {/* Reviews Section */}
      <section id="reviews" className="mt-20 border-t border-border pt-12">
        <div className="max-w-3xl">
          <h2 className="text-2xl font-medium tracking-tight md:text-3xl text-foreground mb-6">
            {t.reviews}
          </h2>

          {getCookie('token') ? (
            <form onSubmit={handleSubmitReview} className="mb-10 rounded-xl border border-border bg-card/60 p-6 space-y-4">
              <div>
                <span className="block text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">
                  {t.rateStars(reviewRating)}
                </span>
                <div className="flex items-center gap-1.5">
                  {[1, 2, 3, 4, 5].map(n => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setReviewRating(n)}
                      aria-label={t.rateStars(n)}
                      className="transition-transform hover:scale-110 active:scale-95 p-1"
                    >
                      <Star
                        width={22}
                        height={22}
                        className={n <= reviewRating ? 'fill-amber-400 text-amber-400' : 'fill-none text-muted-foreground/40'}
                      />
                    </button>
                  ))}
                </div>
              </div>

              <textarea
                value={reviewComment}
                onChange={e => setReviewComment(e.target.value)}
                placeholder={t.sharePlaceholder}
                className="w-full rounded-lg border border-input bg-background p-3 text-sm focus:ring-2 focus:ring-ring outline-none transition-shadow"
                rows={3}
              />
              <button
                type="submit"
                disabled={submittingReview}
                className="px-5 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium transition-colors hover:bg-primary/90 active:scale-[0.98] disabled:opacity-50"
              >
                {submittingReview ? t.submitting : t.submitReview}
              </button>
            </form>
          ) : (
            <div className="mb-8 rounded-lg border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
              <Link href="/login" className="font-medium text-foreground underline underline-offset-4 hover:opacity-80">
                {t.signIn}
              </Link>{' '}
              {t.signInToReview}
            </div>
          )}

          {reviews.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">{t.noReviewsYet}</p>
          ) : (
            <div className="space-y-6">
              {reviews.map((r) => (
                <div key={r.id} className="border-b border-border/60 pb-6 last:border-0">
                  <div className="flex items-center gap-3 mb-2 flex-wrap">
                    <StarRating rating={r.rating} size={14} />
                    <span className="font-medium text-sm text-foreground">{r.customer_name}</span>
                    {r.is_verified_buyer && (
                      <span className="text-[11px] font-medium px-2 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
                        {t.verifiedPurchase}
                      </span>
                    )}
                    <span className="text-xs text-muted-foreground ms-auto">
                      {formatUiDate(r.created_at, lang === 'en' ? 'en' : 'he')}
                    </span>
                  </div>
                  {r.comment && <p className="text-sm text-foreground/80 leading-relaxed mt-1">{r.comment}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
