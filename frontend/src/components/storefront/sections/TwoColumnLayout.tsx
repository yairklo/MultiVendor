import { CSSProperties } from 'react'
import { Section } from '@/lib/ai/types'
import { resolveDesignVariantClasses } from '@/lib/design-tokens'
import { renderSections } from '../PageRenderer'

export function TwoColumnLayout({
  section,
  onAction,
  tenantSlug,
  showTypeLabels,
}: {
  section: Section
  onAction?: (action: any) => void
  tenantSlug?: string
  showTypeLabels?: boolean
}) {
  const containerClass = resolveDesignVariantClasses(section.settings.design_variant)
  const left = section.zones?.left ?? []
  const right = section.zones?.right ?? []
  const split = typeof section.settings.split === 'number' ? section.settings.split : 50

  return (
    <div className={containerClass}>
      <div
        className="grid grid-cols-1 gap-4 md:grid-cols-[var(--split-cols)]"
        style={{ '--split-cols': `${split}% ${100 - split}%` } as CSSProperties}
      >
        <div className="flex flex-col gap-4" data-zone="left">
          {left.length > 0
            ? renderSections(left, { onAction, tenantSlug, showTypeLabels })
            : <div className="p-4 text-center text-sm text-current/60">Empty — left column.</div>}
        </div>
        <div className="flex flex-col gap-4" data-zone="right">
          {right.length > 0
            ? renderSections(right, { onAction, tenantSlug, showTypeLabels })
            : <div className="p-4 text-center text-sm text-current/60">Empty — right column.</div>}
        </div>
      </div>
    </div>
  )
}
