import { CSSProperties } from 'react'
import { Section } from '@/lib/ai/types'

export function Gallery({ section, themeStyle }: { section: Section; themeStyle: CSSProperties }) {
  const layout = section.settings.layout ?? 'grid'
  const images: string[] = Array.isArray(section.settings.images)
    ? section.settings.images.filter((u: unknown) => typeof u === 'string' && u.trim().length > 0)
    : section.media?.url
      ? [section.media.url]
      : []

  return (
    <div
      className="rounded-2xl p-6"
      style={{ ...themeStyle, background: 'var(--section-bg, #f9fafb)', color: 'var(--section-text, #111827)' }}
    >
      {section.settings.title && <h2 className="mb-4 text-xl font-bold">{section.settings.title}</h2>}
      {images.length === 0 ? (
        <div className="grid grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="aspect-square rounded-xl border border-gray-100 bg-white shadow-sm" />
          ))}
        </div>
      ) : layout === 'carousel' ? (
        <div className="flex gap-3 overflow-x-auto pb-1">
          {images.map((url, i) => (
            // eslint-disable-next-line @next/next/no-img-element -- arbitrary AI/admin-authored
            // URLs with no host allowlist; see ProductCard.tsx for why next/image isn't used here.
            <img
              key={i}
              src={url}
              alt=""
              className="aspect-square w-40 flex-none rounded-xl object-cover shadow-sm md:w-56"
            />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {images.map((url, i) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img key={i} src={url} alt="" className="aspect-square w-full rounded-xl object-cover shadow-sm" />
          ))}
        </div>
      )}
    </div>
  )
}
