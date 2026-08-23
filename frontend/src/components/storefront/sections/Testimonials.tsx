import { CSSProperties } from 'react'
import { Quote } from 'lucide-react'
import { LocalizedText, Section } from '@/lib/ai/types'
import { resolveI18nText } from '@/lib/i18n-text'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'

type TestimonialItem = { quote?: LocalizedText; author?: LocalizedText; role?: LocalizedText }

export function Testimonials({ section, themeStyle }: { section: Section; themeStyle: CSSProperties }) {
  const { lang } = useStorefrontTheme()
  const items: TestimonialItem[] = Array.isArray(section.settings.items) ? section.settings.items : []
  const title = resolveI18nText(section.settings.title, lang)

  return (
    <div
      className="rounded-2xl p-6"
      style={{ ...themeStyle, background: 'var(--section-bg, transparent)', color: 'var(--section-text, inherit)' }}
    >
      {title && <h2 className="mb-4 text-xl font-bold">{title}</h2>}
      {items.length === 0 ? (
        <span className="text-sm text-current/50">No testimonials configured.</span>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {items.map((item, i) => {
            const role = resolveI18nText(item.role, lang)
            return (
              <figure key={i} className="flex flex-col gap-3 rounded-xl border border-current/10 bg-current/[0.03] p-5">
                <Quote className="h-5 w-5 text-current/40" strokeWidth={1.75} />
                <blockquote className="flex-1 text-sm italic text-current/80">&ldquo;{resolveI18nText(item.quote, lang)}&rdquo;</blockquote>
                <figcaption className="text-sm font-semibold">
                  {resolveI18nText(item.author, lang)}
                  {role && <span className="font-normal text-current/60"> &middot; {role}</span>}
                </figcaption>
              </figure>
            )
          })}
        </div>
      )}
    </div>
  )
}
