'use client'

import React, { useState, useEffect } from 'react'
import { useReviews } from '@/hooks/useReviews'
import { useToast } from '@/context/ToastContext'
import { Button } from '@/components/ui/button'
import { StarRating } from '@/components/ui/star-rating'

export default function ReviewsPage() {
  const { fetchReviews, updateReviewStatus } = useReviews()
  const { showToast } = useToast()
  const [reviews, setReviews] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)

  useEffect(() => {
    loadReviews()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadReviews = async () => {
    setLoading(true)
    const data = await fetchReviews()
    setReviews(data)
    setLoading(false)
  }

  const handleStatus = async (reviewId: number, status: 'approved' | 'rejected') => {
    setBusyId(reviewId)
    try {
      await updateReviewStatus(reviewId, status)
      await loadReviews()
      showToast(status === 'approved' ? 'Review approved' : 'Review rejected', 'success')
    } catch (e: any) {
      showToast(e.message || 'Failed to update review', 'error')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Reviews</h1>

      {loading ? (
        <div className="text-gray-500">Loading reviews...</div>
      ) : reviews.length === 0 ? (
        <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-100 text-center text-gray-500">
          No reviews yet.
        </div>
      ) : (
        <div className="space-y-4">
          {reviews.map(review => (
            <div key={review.id} className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <div className="font-bold text-gray-900">{review.product_name}</div>
                  <div className="text-sm text-gray-500">by {review.customer_name}</div>
                </div>
                <div className="flex items-center gap-2">
                  <StarRating rating={review.rating} />
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                    review.is_approved ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {review.is_approved ? 'Approved' : 'Pending'}
                  </span>
                </div>
              </div>

              {review.comment && <p className="text-gray-700 mb-4">{review.comment}</p>}

              <div className="flex gap-2">
                <Button
                  size="sm"
                  disabled={busyId === review.id || review.is_approved}
                  onClick={() => handleStatus(review.id, 'approved')}
                >
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  disabled={busyId === review.id || !review.is_approved}
                  onClick={() => handleStatus(review.id, 'rejected')}
                >
                  Reject
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
