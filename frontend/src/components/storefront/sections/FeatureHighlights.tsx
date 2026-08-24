import { CSSProperties } from 'react'
import {
  Truck, ShieldCheck, RotateCcw, Sparkles, Heart, Gift, Clock, Award, Leaf, CreditCard,
  Headphones, PackageCheck, LucideIcon,
} from 'lucide-react'
import { LocalizedText, Section } from '@/lib/ai/types'
import { resolveI18nText } from '@/lib/i18n-text'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'

const ICONS: Record<string, LucideIcon> = {
  Truck, ShieldCheck, RotateCcw, Sparkles, Heart, Gift, Clock, Award, Leaf, CreditCard,
  Headphones, PackageCheck,
}

type HighlightItem = { icon?: string; title?: LocalizedText; text?: LocalizedText }

export function FeatureHighlights({ section, themeStyle }: { section: Section; themeStyle: CSSProperties }) {
  const { lang } = useStorefrontTheme()
  const items: HighlightItem[] = Array.isArray(section.settings.items) ? section.settings.items : []
  const title = resolveI18nText(section.settings.title, lang)

  return (
    <div
      className="rounded-2xl p-6"
      style={{ ...themeStyle, background: 'var(--section-bg, transparent)', color: 'var(--section-text, inherit)' }}
    >
      {title && <h2 className="mb-4 text-xl font-bold">{title}</h2>}
      {items.length === 0 ? (
        <span className="text-sm text-current/50">No highlights configured.</span>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3">
          {items.map((item, i) => {
            const Icon = (item.icon && ICONS[item.icon]) || Sparkles
            const text = resolveI18nText(item.text, lang)
            return (
              <div key={i} className="flex flex-col items-center gap-2 text-center">
                <span className="flex h-12 w-12 items-center justify-center rounded-full bg-current/5 transition-colors duration-200 hover:bg-current/10">
                  <Icon className="h-6 w-6" strokeWidth={1.75} />
                </span>
                <h3 className="font-semibold">{resolveI18nText(item.title, lang)}</h3>
                {text && <p className="text-sm text-current/70">{text}</p>}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
