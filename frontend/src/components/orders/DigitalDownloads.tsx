'use client'

import { resolveImageUrl } from '@/lib/media'

type DownloadableItem = {
  id: number
  product_name?: string
  download_url?: string | null
}

export function DigitalDownloads({
  items,
  label,
  heading,
}: {
  items: DownloadableItem[] | undefined
  label: string
  heading?: string
}) {
  const downloads = (items || []).filter((item) => item.download_url)
  if (downloads.length === 0) return null

  return (
    <div className="mt-4 space-y-2">
      {heading && <p className="text-sm font-medium text-foreground">{heading}</p>}
      <ul className="space-y-1.5">
        {downloads.map((item) => (
          <li key={item.id}>
            <a
              href={resolveImageUrl(item.download_url)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center text-sm font-medium text-primary underline-offset-4 transition-colors duration-150 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
            >
              {label}
              {item.product_name ? ` — ${item.product_name}` : ''}
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}
