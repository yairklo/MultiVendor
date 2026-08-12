import { CSSProperties } from 'react'
import { Section } from '@/lib/ai/types'

const SIZE_HEIGHTS: Record<string, number> = { small: 160, medium: 280, large: 420 }

export function HeroBanner({ section, themeStyle }: { section: Section; themeStyle: CSSProperties }) {
  const size = section.settings.size ?? 'medium'
  const height = SIZE_HEIGHTS[size] ?? SIZE_HEIGHTS.medium
  const alignment = section.settings.alignment === 'left' ? 'items-start text-left' : section.settings.alignment === 'right' ? 'items-end text-right' : 'items-center text-center'
  const imageUrl = section.media?.type === 'image' ? section.media.url : undefined

  return (
    <div
      className={`relative flex flex-col justify-center gap-3 overflow-hidden rounded-2xl px-8 ${alignment}`}
      style={{
        ...themeStyle,
        height,
        background: imageUrl ? undefined : 'var(--section-bg, linear-gradient(135deg, #eef2ff, #e0e7ff))',
        color: imageUrl ? '#ffffff' : 'var(--section-text, #1e293b)',
      }}
    >
      {imageUrl && (
        <>
          <img src={imageUrl} alt="" className="absolute inset-0 h-full w-full object-cover" />
          <div className="absolute inset-0 bg-black/35" />
        </>
      )}
      <h1 className="relative z-10 text-3xl font-bold md:text-4xl">{section.settings.headline ?? 'Hero Banner'}</h1>
    </div>
  )
}
