'use client'

import React, { useState } from 'react'
import { useReviews } from '@/hooks/useReviews'
import { useToast } from '@/context/ToastContext'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { StarRating } from '@/components/ui/star-rating'

export function ReviewsPageClient({ initialReviews }: { initialReviews: any[] }) {
  const { fetchReviews, updateReviewStatus } = useReviews()
  const { showToast } = useToast()
  const [reviews, setReviews] = useState<any[]>(initialReviews)
  const [busyId, setBusyId] = useState<number | null>(null)

  const loadReviews = async () => {
    const data = await fetchReviews()
    setReviews(data)
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
      <h1 className="font-heading text-3xl font-bold text-foreground mb-8">Reviews</h1>

      {reviews.length === 0 ? (
        <div className="bg-card p-8 rounded-xl shadow-sm border border-border text-center text-muted-foreground">
          No reviews yet.
        </div>
      ) : (
        <div className="space-y-4">
          {reviews.map(review => (
            <div key={review.id} className="bg-card p-6 rounded-xl shadow-sm border border-border transition-shadow hover:shadow-md">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <div className="font-bold text-foreground">{review.product_name}</div>
                  <div className="text-sm text-muted-foreground">by {review.customer_name}</div>
                </div>
                <div className="flex items-center gap-2">
                  <StarRating rating={review.rating} />
                  <Badge variant={review.is_approved ? 'success' : 'warning'}>
                    {review.is_approved ? 'Approved' : 'Pending'}
                  </Badge>
                </div>
              </div>

              {review.comment && <p className="text-foreground/80 mb-4">{review.comment}</p>}

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
