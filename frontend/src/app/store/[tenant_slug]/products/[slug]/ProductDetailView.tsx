'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { getCookie } from 'cookies-next'
import { apiClient, ApiError } from '@/lib/api/apiClient'
import { useCart } from '@/context/CartContext'
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
}: {
  tenantSlug: string
  slug: string
  product: Product
  initialReviews: ProductReview[]
}) {
  const [quantity, setQuantity] = useState(1)
  const [adding, setAdding] = useState(false)
  const [reviews, setReviews] = useState<ProductReview[]>(initialReviews)
  const [reviewRating, setReviewRating] = useState(5)
  const [reviewComment, setReviewComment] = useState('')
  const [submittingReview, setSubmittingReview] = useState(false)
  const { addItem, openDrawer } = useCart()
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

  const clampQuantity = (qty: number) => Math.max(1, Math.min(qty, stockKnown ? Math.max(stock, 1) : qty))

  const handleAddToCart = async () => {
    const variantId = product.variants?.[0]?.id
    if (!variantId) return
    setAdding(true)
    try {
      await addItem(tenantSlug, variantId, quantity)
      openDrawer()
    } catch (e) {
      console.error('Failed to add item to cart:', e)
    } finally {
      setAdding(false)
    }
  }

  return (
    <div className="p-4 bg-gray-50 min-h-screen text-gray-900">
      <div className="max-w-4xl mx-auto">
        <Link href={`/store/${tenantSlug}`} className="inline-flex items-center text-blue-600 transition-colors hover:text-blue-700 hover:underline">
          {t.backToStore}
        </Link>

        <div className="mt-4 bg-white rounded-xl shadow-sm border border-gray-100 p-6 grid grid-cols-1 md:grid-cols-2 gap-8 transition-shadow duration-300 hover:shadow-md">
          <div>
            {images.length > 0 ? (
              // Arbitrary vendor-supplied URLs with no host allowlist, same
              // reasoning as storefront/ProductCard.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={resolveImageUrl(images[0])} alt={name} className="w-full h-80 object-cover rounded-lg" />
            ) : (
              <div className="w-full h-80 bg-gray-100 rounded-lg flex items-center justify-center text-gray-400">
                {t.noImage}
              </div>
            )}
          </div>

          <div className="flex flex-col">
            <h1 className={`text-2xl font-bold mb-2 ${theme.headingFont}`}>{name}</h1>
            {product.review_count > 0 && (
              <div className="flex items-center gap-2 mb-2">
                <StarRating rating={product.average_rating ?? 0} />
                <span className="text-sm text-gray-500">
                  {product.average_rating} ({product.review_count} {t.reviewWord(product.review_count)})
                </span>
              </div>
            )}
            <p className="text-xl text-gray-700 mb-4">{formatCurrency(product.base_price)}</p>
            {description && <p className="text-gray-600 mb-4 leading-relaxed">{description}</p>}

            {digital ? (
              <p className="text-sm mb-4 text-muted-foreground">{t.digitalDelivery}</p>
            ) : stockKnown && (
              <p className={`text-sm mb-4 ${outOfStock ? 'text-red-600 font-medium' : 'text-gray-400'}`}>
                {outOfStock ? t.outOfStock : t.inStock(stock)}
              </p>
            )}

            {!outOfStock && (
              <div className="flex items-center gap-2 mb-4">
                <button
                  type="button"
                  aria-label={t.decreaseQuantity}
                  onClick={() => setQuantity(q => clampQuantity(q - 1))}
                  className="w-8 h-8 border rounded-lg text-gray-700 transition-colors hover:bg-gray-100 active:scale-95"
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
                  className="w-14 text-center border rounded-lg py-1"
                />
                <button
                  type="button"
                  aria-label={t.increaseQuantity}
                  onClick={() => setQuantity(q => clampQuantity(q + 1))}
                  className="w-8 h-8 border rounded-lg text-gray-700 transition-colors hover:bg-gray-100 active:scale-95"
                >
                  +
                </button>
              </div>
            )}

            <button
              onClick={handleAddToCart}
              disabled={outOfStock || adding}
              className={`mt-auto w-full px-4 py-3 font-medium transition-all duration-150 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed ${theme.primaryButtonClass}`}
            >
              {outOfStock ? t.outOfStock : adding ? t.adding : t.addToCart}
            </button>
          </div>
        </div>

        <div className="mt-6 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-xl font-bold mb-4">{t.reviews}</h2>

          {getCookie('token') ? (
            <form onSubmit={handleSubmitReview} className="mb-6 pb-6 border-b space-y-3">
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map(n => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setReviewRating(n)}
                    aria-label={t.rateStars(n)}
                    className="transition-transform hover:scale-110"
                  >
                    <Star
                      width={22}
                      height={22}
                      className={n <= reviewRating ? 'fill-amber-400 text-amber-400' : 'fill-none text-gray-300'}
                    />
                  </button>
                ))}
              </div>
              <textarea
                value={reviewComment}
                onChange={e => setReviewComment(e.target.value)}
                placeholder={t.sharePlaceholder}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-600 outline-none transition-shadow"
                rows={3}
              />
              <button
                type="submit"
                disabled={submittingReview}
                className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium transition-colors duration-150 hover:bg-gray-800 active:scale-[0.98] disabled:opacity-50"
              >
                {submittingReview ? t.submitting : t.submitReview}
              </button>
            </form>
          ) : (
            <p className="text-sm text-gray-500 mb-6 pb-6 border-b">
              <Link href="/login" className="text-blue-600 transition-colors hover:text-blue-700 hover:underline">{t.signIn}</Link> {t.signInToReview}
            </p>
          )}

          {reviews.length === 0 ? (
            <p className="text-gray-500 text-sm">{t.noReviewsYet}</p>
          ) : (
            <div className="space-y-4">
              {reviews.map((r) => (
                <div key={r.id} className="border-b last:border-0 pb-4 last:pb-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <StarRating rating={r.rating} size={14} />
                    <span className="font-medium text-sm">{r.customer_name}</span>
                    {r.is_verified_buyer && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">{t.verifiedPurchase}</span>
                    )}
                  </div>
                  {r.comment && <p className="text-gray-600 text-sm">{r.comment}</p>}
                  <p className="text-xs text-gray-400 mt-1">{formatUiDate(r.created_at, lang === 'en' ? 'en' : 'he')}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
