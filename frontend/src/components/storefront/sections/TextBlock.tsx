import { CSSProperties } from 'react'
import { Section } from '@/lib/ai/types'

export function TextBlock({ section, themeStyle }: { section: Section; themeStyle: CSSProperties }) {
  const fontSize = typeof section.settings.font_size === 'string' && section.settings.font_size ? section.settings.font_size : undefined
  return (
    <div
      className="rounded-2xl p-6"
      style={{
        ...themeStyle,
        background: 'var(--section-bg, #ffffff)',
        color: 'var(--section-text, #111827)',
        fontFamily: 'var(--section-font, inherit)',
      }}
    >
      <h2 className="mb-2 text-xl font-bold" style={fontSize ? { fontSize } : undefined}>{section.settings.heading ?? 'Text'}</h2>
      <p className="leading-relaxed text-current/80">{section.settings.body ?? ''}</p>
    </div>
  )
}
