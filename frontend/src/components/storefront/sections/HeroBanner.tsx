import { CSSProperties, FocusEvent } from 'react'
import { Section } from '@/lib/ai/types'
import { resolveI18nText } from '@/lib/i18n-text'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'

const SIZE_HEIGHTS: Record<string, number> = { small: 160, medium: 280, large: 420 }

export function HeroBanner({
  section, themeStyle, onInlineEdit,
}: { section: Section; themeStyle: CSSProperties; onInlineEdit?: (sectionId: string, patch: Partial<Section>) => void }) {
  const { lang } = useStorefrontTheme()
  const size = typeof section.settings.size === 'string' ? section.settings.size : 'medium'
  const height = SIZE_HEIGHTS[size] ?? SIZE_HEIGHTS.medium
  const alignment = section.settings.alignment === 'left' ? 'items-start text-left' : section.settings.alignment === 'right' ? 'items-end text-right' : 'items-center text-center'
  const imageUrl = section.media?.type === 'image' ? section.media.url : undefined
  const fontSize = typeof section.settings.font_size === 'string' && section.settings.font_size ? section.settings.font_size : undefined
  const headline = resolveI18nText(section.settings.headline, lang) || 'Hero Banner'

  const handleHeadlineBlur = (e: FocusEvent<HTMLHeadingElement>) => {
    const next = e.currentTarget.textContent ?? ''
    if (next !== headline) {
      onInlineEdit?.(section.id, {
        settings: {
          ...section.settings,
          headline: { ...(section.settings.headline as Record<string, string> | undefined), [lang]: next },
        },
      })
    }
  }

  return (
    <div
      className={`relative flex flex-col justify-center gap-3 overflow-hidden rounded-2xl px-8 ${alignment}`}
      style={{
        ...themeStyle,
        height,
        background: imageUrl ? undefined : 'var(--section-bg, oklch(0.93 0.02 78))',
        color: imageUrl ? '#ffffff' : 'var(--section-text, oklch(0.2 0.025 48))',
        fontFamily: 'var(--section-font, inherit)',
      }}
    >
      {imageUrl && (
        <>
          {/* Arbitrary AI/admin-authored URL with no host allowlist; see
              ProductCard.tsx for why next/image isn't used here. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={imageUrl} alt="" className="absolute inset-0 h-full w-full object-cover" />
          <div className="absolute inset-0 bg-black/35" />
        </>
      )}
      <h1
        className={`relative z-10 text-3xl font-bold md:text-4xl${onInlineEdit ? ' cursor-text rounded outline-none transition-colors hover:bg-black/5 focus:bg-black/5 focus:ring-2 focus:ring-indigo-400' : ''}`}
        style={fontSize ? { fontSize } : undefined}
        contentEditable={!!onInlineEdit}
        suppressContentEditableWarning={!!onInlineEdit}
        onBlur={onInlineEdit ? handleHeadlineBlur : undefined}
      >
        {headline}
      </h1>
    </div>
  )
}
