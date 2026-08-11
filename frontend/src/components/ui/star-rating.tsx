import { Star } from 'lucide-react'
import { cn } from '@/lib/utils'

export function StarRating({ rating, size = 16, className }: { rating: number; size?: number; className?: string }) {
  const rounded = Math.round(rating)
  return (
    <span className={cn('inline-flex items-center gap-0.5', className)} aria-label={`${rating} out of 5 stars`}>
      {Array.from({ length: 5 }, (_, i) => (
        <Star
          key={i}
          width={size}
          height={size}
          className={i < rounded ? 'fill-amber-400 text-amber-400' : 'fill-none text-gray-300'}
        />
      ))}
    </span>
  )
}
