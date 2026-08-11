import { CSSProperties } from 'react'
import { Section } from '@/lib/ai/types'

export function VideoEmbed({ section, themeStyle }: { section: Section; themeStyle: CSSProperties }) {
  return (
    <div
      className="rounded-2xl p-6"
      style={{ ...themeStyle, background: 'var(--section-bg, #111827)', color: 'var(--section-text, #ffffff)' }}
    >
      <h2 className="mb-3 text-xl font-bold">{section.settings.title ?? 'Video'}</h2>
      <div className="flex aspect-video items-center justify-center rounded-xl bg-black/30">
        <span>▶ {section.media?.url ?? 'no media set'}</span>
      </div>
      {section.settings.autoplay && (
        <span className="mt-2 inline-block rounded-full bg-white/20 px-2 py-0.5 text-xs">autoplay</span>
      )}
    </div>
  )
}
