'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { getCookie } from 'cookies-next'
import { apiClient, ApiError } from '@/lib/api/apiClient'
import { useCart } from '@/context/CartContext'
import { useToast } from '@/context/ToastContext'
import { totalStock } from '@/lib/stock'
import { StarRating } from '@/components/ui/star-rating'
import { Star } from 'lucide-react'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'
import { useCurrency } from '@/hooks/useCurrency'
import { resolveImageUrl } from '@/lib/media'

export function ProductDetailView({
  tenantSlug,
  slug,
  product,
  initialReviews,
}: {
  tenantSlug: string
  slug: string
  product: any
  initialReviews: any[]
}) {
  const [quantity, setQuantity] = useState(1)
  const [adding, setAdding] = useState(false)
  const [reviews, setReviews] = useState<any[]>(initialReviews)
  const [reviewRating, setReviewRating] = useState(5)
  const [reviewComment, setReviewComment] = useState('')
  const [submittingReview, setSubmittingReview] = useState(false)
  const { addItem, openDrawer } = useCart()
  const { showToast } = useToast()
  const { theme } = useStorefrontTheme()
  const { formatCurrency } = useCurrency()

  const loadReviews = () => {
    apiClient(`/api/v1/store/${tenantSlug}/products/${slug}/reviews`)
      .then(setReviews)
      .catch((e: any) => console.error('Failed to load reviews:', e))
  }

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmittingReview(true)
    try {
      await apiClient(`/api/v1/store/${tenantSlug}/reviews`, {
        method: 'POST',
        body: JSON.stringify({ product_id: product.id, rating: reviewRating, comment: reviewComment || undefined }),
      })
      showToast('Thanks for your review!', 'success')
      setReviewComment('')
      setReviewRating(5)
      loadReviews()
    } catch (e: any) {
      if (e instanceof ApiError && e.status === 400) {
        showToast("You've already reviewed this product.", 'error')
      } else {
        showToast(e.message || 'Failed to submit review', 'error')
      }
    } finally {
      setSubmittingReview(false)
    }
  }

  const stock = totalStock(product.variants)
  const stockKnown = Number.isFinite(stock)
  const outOfStock = stockKnown && stock <= 0
  const name = typeof product.name === 'object' ? (product.name?.en || product.name?.he) : product.name
  const description = typeof product.description === 'object' ? (product.description?.en || product.description?.he) : product.description
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
        <Link href={`/store/${tenantSlug}`} className="text-blue-600 hover:underline">&larr; Back to store</Link>

        <div className="mt-4 bg-white rounded-xl shadow-md border border-gray-100 p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            {images.length > 0 ? (
              <img src={resolveImageUrl(images[0])} alt={name} className="w-full h-80 object-cover rounded-lg" />
            ) : (
              <div className="w-full h-80 bg-gray-100 rounded-lg flex items-center justify-center text-gray-400">
                No image
              </div>
            )}
          </div>

          <div>
            <h1 className={`text-2xl font-bold mb-2 ${theme.headingFont}`}>{name}</h1>
            {product.review_count > 0 && (
              <div className="flex items-center gap-2 mb-2">
                <StarRating rating={product.average_rating} />
                <span className="text-sm text-gray-500">
                  {product.average_rating} ({product.review_count} review{product.review_count === 1 ? '' : 's'})
                </span>
              </div>
            )}
            <p className="text-xl text-gray-700 mb-4">{formatCurrency(product.base_price)}</p>
            {description && <p className="text-gray-600 mb-4">{description}</p>}

            {stockKnown && (
              <p className={`text-sm mb-4 ${outOfStock ? 'text-red-600 font-medium' : 'text-gray-400'}`}>
                {outOfStock ? 'Out of stock' : `${stock} in stock`}
              </p>
            )}

            {!outOfStock && (
              <div className="flex items-center gap-2 mb-4">
                <button
                  type="button"
                  aria-label="Decrease quantity"
                  onClick={() => setQuantity(q => clampQuantity(q - 1))}
                  className="w-8 h-8 border rounded-lg text-gray-700 hover:bg-gray-100"
                >
                  &minus;
                </button>
                <input
                  type="number"
                  aria-label="Quantity"
                  min={1}
                  max={stockKnown ? stock : undefined}
                  value={quantity}
                  onChange={e => setQuantity(clampQuantity(Number(e.target.value) || 1))}
                  className="w-14 text-center border rounded-lg py-1"
                />
                <button
                  type="button"
                  aria-label="Increase quantity"
                  onClick={() => setQuantity(q => clampQuantity(q + 1))}
                  className="w-8 h-8 border rounded-lg text-gray-700 hover:bg-gray-100"
                >
                  +
                </button>
              </div>
            )}

            <button
              onClick={handleAddToCart}
              disabled={outOfStock || adding}
              className={`w-full px-4 py-3 font-medium active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed ${theme.primaryButtonClass}`}
            >
              {outOfStock ? 'Out of stock' : adding ? 'Adding...' : 'Add to Cart'}
            </button>
          </div>
        </div>

        <div className="mt-6 bg-white rounded-xl shadow-md border border-gray-100 p-6">
          <h2 className="text-xl font-bold mb-4">Reviews</h2>

          {getCookie('token') ? (
            <form onSubmit={handleSubmitReview} className="mb-6 pb-6 border-b space-y-3">
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map(n => (
                  <button key={n} type="button" onClick={() => setReviewRating(n)} aria-label={`Rate ${n} stars`}>
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
                placeholder="Share your thoughts about this product..."
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-600 outline-none"
                rows={3}
              />
              <button
                type="submit"
                disabled={submittingReview}
                className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50"
              >
                {submittingReview ? 'Submitting...' : 'Submit Review'}
              </button>
            </form>
          ) : (
            <p className="text-sm text-gray-500 mb-6 pb-6 border-b">
              <Link href="/login" className="text-blue-600 hover:underline">Sign in</Link> to write a review.
            </p>
          )}

          {reviews.length === 0 ? (
            <p className="text-gray-500 text-sm">No reviews yet.</p>
          ) : (
            <div className="space-y-4">
              {reviews.map((r: any) => (
                <div key={r.id} className="border-b last:border-0 pb-4 last:pb-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <StarRating rating={r.rating} size={14} />
                    <span className="font-medium text-sm">{r.customer_name}</span>
                    {r.is_verified_buyer && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">Verified Purchase</span>
                    )}
                  </div>
                  {r.comment && <p className="text-gray-600 text-sm">{r.comment}</p>}
                  <p className="text-xs text-gray-400 mt-1">{new Date(r.created_at).toLocaleDateString()}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
