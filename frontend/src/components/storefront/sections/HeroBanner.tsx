import { CSSProperties, FocusEvent } from 'react'
import { Section } from '@/lib/ai/types'

const SIZE_HEIGHTS: Record<string, number> = { small: 160, medium: 280, large: 420 }

export function HeroBanner({
  section, themeStyle, onInlineEdit,
}: { section: Section; themeStyle: CSSProperties; onInlineEdit?: (sectionId: string, patch: Partial<Section>) => void }) {
  const size = section.settings.size ?? 'medium'
  const height = SIZE_HEIGHTS[size] ?? SIZE_HEIGHTS.medium
  const alignment = section.settings.alignment === 'left' ? 'items-start text-left' : section.settings.alignment === 'right' ? 'items-end text-right' : 'items-center text-center'
  const fontSize = typeof section.settings.font_size === 'string' && section.settings.font_size ? section.settings.font_size : undefined
  const headline = section.settings.headline ?? 'Hero Banner'

  const handleHeadlineBlur = (e: FocusEvent<HTMLHeadingElement>) => {
    const next = e.currentTarget.textContent ?? ''
    if (next !== headline) onInlineEdit?.(section.id, { settings: { ...section.settings, headline: next } })
  }

  return (
    <div
      className={`flex flex-col justify-center gap-3 rounded-2xl px-8 ${alignment}`}
      style={{
        ...themeStyle,
        height,
        background: 'var(--section-bg, linear-gradient(135deg, #eef2ff, #e0e7ff))',
        color: 'var(--section-text, #1e293b)',
        fontFamily: 'var(--section-font, inherit)',
      }}
    >
      <span className="inline-block w-fit rounded-full bg-white/70 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-blue-700">
        {size}
      </span>
      <h1
        className={`text-3xl font-bold md:text-4xl${onInlineEdit ? ' cursor-text rounded outline-none hover:bg-black/5 focus:bg-black/5 focus:ring-2 focus:ring-indigo-400' : ''}`}
        style={fontSize ? { fontSize } : undefined}
        contentEditable={!!onInlineEdit}
        suppressContentEditableWarning={!!onInlineEdit}
        onBlur={onInlineEdit ? handleHeadlineBlur : undefined}
      >
        {headline}
      </h1>
      {section.media && (
        <span className="text-xs text-current/70">image: {section.media.url}</span>
      )}
    </div>
  )
}
