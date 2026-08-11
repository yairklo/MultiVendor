import { CSSProperties } from 'react'
import { Section } from '@/lib/ai/types'

export function TextBlock({ section, themeStyle }: { section: Section; themeStyle: CSSProperties }) {
  return (
    <div
      className="rounded-2xl p-6"
      style={{ ...themeStyle, background: 'var(--section-bg, #ffffff)', color: 'var(--section-text, #111827)' }}
    >
      <h2 className="mb-2 text-xl font-bold">{section.settings.heading ?? 'Text'}</h2>
      <p className="leading-relaxed text-current/80">{section.settings.body ?? ''}</p>
    </div>
  )
}
