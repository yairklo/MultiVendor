import { CSSProperties } from 'react'
import { Section } from '@/lib/ai/types'

const SIZE_HEIGHTS: Record<string, number> = { small: 160, medium: 280, large: 420 }

export function HeroBanner({ section, themeStyle }: { section: Section; themeStyle: CSSProperties }) {
  const size = section.settings.size ?? 'medium'
  const height = SIZE_HEIGHTS[size] ?? SIZE_HEIGHTS.medium
  const alignment = section.settings.alignment === 'left' ? 'items-start text-left' : section.settings.alignment === 'right' ? 'items-end text-right' : 'items-center text-center'

  return (
    <div
      className={`flex flex-col justify-center gap-3 rounded-2xl px-8 ${alignment}`}
      style={{
        ...themeStyle,
        height,
        background: 'var(--section-bg, linear-gradient(135deg, #eef2ff, #e0e7ff))',
        color: 'var(--section-text, #1e293b)',
      }}
    >
      <span className="inline-block w-fit rounded-full bg-white/70 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-blue-700">
        {size}
      </span>
      <h1 className="text-3xl font-bold md:text-4xl">{section.settings.headline ?? 'Hero Banner'}</h1>
      {section.media && (
        <span className="text-xs text-current/70">image: {section.media.url}</span>
      )}
    </div>
  )
}
