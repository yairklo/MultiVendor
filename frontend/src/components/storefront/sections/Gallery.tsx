import { CSSProperties } from 'react'
import { Section } from '@/lib/ai/types'

export function Gallery({ section, themeStyle }: { section: Section; themeStyle: CSSProperties }) {
  const layout = section.settings.layout ?? 'grid'

  return (
    <div
      className="rounded-2xl p-6"
      style={{ ...themeStyle, background: 'var(--section-bg, #f9fafb)', color: 'var(--section-text, #111827)' }}
    >
      <h2 className="mb-4 text-xl font-bold">Gallery ({layout})</h2>
      <div className="grid grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="aspect-square rounded-xl border border-gray-100 bg-white shadow-sm" />
        ))}
      </div>
      {section.media && <div className="mt-3 text-xs text-current/60">media: {section.media.url}</div>}
    </div>
  )
}
