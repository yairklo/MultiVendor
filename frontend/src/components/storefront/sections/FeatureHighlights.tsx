import { CSSProperties } from 'react'
import {
  Truck, ShieldCheck, RotateCcw, Sparkles, Heart, Gift, Clock, Award, Leaf, CreditCard,
  Headphones, PackageCheck, LucideIcon,
} from 'lucide-react'
import { Section } from '@/lib/ai/types'

const ICONS: Record<string, LucideIcon> = {
  Truck, ShieldCheck, RotateCcw, Sparkles, Heart, Gift, Clock, Award, Leaf, CreditCard,
  Headphones, PackageCheck,
}

type HighlightItem = { icon?: string; title?: string; text?: string }

export function FeatureHighlights({ section, themeStyle }: { section: Section; themeStyle: CSSProperties }) {
  const items: HighlightItem[] = Array.isArray(section.settings.items) ? section.settings.items : []

  return (
    <div
      className="rounded-2xl p-6"
      style={{ ...themeStyle, background: 'var(--section-bg, transparent)', color: 'var(--section-text, inherit)' }}
    >
      {section.settings.title && <h2 className="mb-4 text-xl font-bold">{section.settings.title}</h2>}
      {items.length === 0 ? (
        <span className="text-sm text-current/50">No highlights configured.</span>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3">
          {items.map((item, i) => {
            const Icon = (item.icon && ICONS[item.icon]) || Sparkles
            return (
              <div key={i} className="flex flex-col items-center gap-2 text-center">
                <span className="flex h-12 w-12 items-center justify-center rounded-full bg-current/5">
                  <Icon className="h-6 w-6" strokeWidth={1.75} />
                </span>
                <h3 className="font-semibold">{item.title}</h3>
                {item.text && <p className="text-sm text-current/70">{item.text}</p>}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
