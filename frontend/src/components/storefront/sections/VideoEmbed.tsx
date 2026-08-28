import { CSSProperties } from 'react'
import { Section } from '@/lib/ai/types'
import { resolveI18nText } from '@/lib/i18n-text'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'

export function VideoEmbed({ section, themeStyle }: { section: Section; themeStyle: CSSProperties }) {
  const { lang } = useStorefrontTheme()
  return (
    <div
      className="rounded-2xl p-6"
      style={{ ...themeStyle, background: 'var(--section-bg, #111827)', color: 'var(--section-text, #ffffff)' }}
    >
      <h2 className="mb-3 text-xl font-bold">{resolveI18nText(section.settings.title, lang) || 'Video'}</h2>
      <div className="flex aspect-video items-center justify-center rounded-xl bg-black/30">
        <span>▶ {section.media?.url ?? 'no media set'}</span>
      </div>
      {!!section.settings.autoplay && (
        <span className="mt-2 inline-block rounded-full bg-white/20 px-2 py-0.5 text-xs">autoplay</span>
      )}
    </div>
  )
}
