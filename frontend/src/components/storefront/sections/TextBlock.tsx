import { CSSProperties, FocusEvent } from 'react'
import { Section } from '@/lib/ai/types'
import { resolveI18nText } from '@/lib/i18n-text'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'

export function TextBlock({
  section, themeStyle, onInlineEdit,
}: { section: Section; themeStyle: CSSProperties; onInlineEdit?: (sectionId: string, patch: Partial<Section>) => void }) {
  const { lang } = useStorefrontTheme()
  const fontSize = typeof section.settings.font_size === 'string' && section.settings.font_size ? section.settings.font_size : undefined
  const heading = resolveI18nText(section.settings.heading, lang) || 'Text'
  const body = resolveI18nText(section.settings.body, lang)
  const editableClass = onInlineEdit ? ' cursor-text rounded outline-none transition-colors hover:bg-black/5 focus:bg-black/5 focus:ring-2 focus:ring-indigo-400' : ''

  const commit = (key: 'heading' | 'body', current: string) => (e: FocusEvent<HTMLElement>) => {
    const next = e.currentTarget.textContent ?? ''
    if (next !== current) {
      onInlineEdit?.(section.id, {
        settings: {
          ...section.settings,
          [key]: { ...(section.settings[key] as Record<string, string> | undefined), [lang]: next },
        },
      })
    }
  }

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
      <h2
        className={`mb-2 text-xl font-bold${editableClass}`}
        style={fontSize ? { fontSize } : undefined}
        contentEditable={!!onInlineEdit}
        suppressContentEditableWarning={!!onInlineEdit}
        onBlur={onInlineEdit ? commit('heading', heading) : undefined}
      >
        {heading}
      </h2>
      <p
        className={`leading-relaxed text-current/80${editableClass}`}
        contentEditable={!!onInlineEdit}
        suppressContentEditableWarning={!!onInlineEdit}
        onBlur={onInlineEdit ? commit('body', body) : undefined}
      >
        {body}
      </p>
    </div>
  )
}
