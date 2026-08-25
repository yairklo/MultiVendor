import { cn } from '@/lib/utils'

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-gray-200', className)} />
}

export function TableRowSkeleton({ columns }: { columns: number }) {
  return (
    <tr>
      {Array.from({ length: columns }, (_, i) => (
        <td key={i} className="border-b border-border/70 px-4 py-3.5 first:ps-5 last:pe-5">
          <Skeleton className="h-4 w-full max-w-[160px] bg-muted" />
        </td>
      ))}
    </tr>
  )
}

export function ProductCardSkeleton() {
  return (
    <div className="bg-white border border-gray-100 p-5 rounded-xl shadow-md">
      <Skeleton className="h-5 w-3/4 mb-3" />
      <Skeleton className="h-4 w-1/3 mb-4" />
      <Skeleton className="h-4 w-1/2 mb-4" />
      <Skeleton className="h-9 w-full" />
    </div>
  )
}
