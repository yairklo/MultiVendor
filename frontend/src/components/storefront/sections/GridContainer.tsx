import { Section, DispatchedAction } from '@/lib/ai/types'
import { resolveDesignVariantClasses } from '@/lib/design-tokens'
import { renderSections } from '../PageRenderer'

const COLUMN_CLASSES: Record<number, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-1 sm:grid-cols-2',
  3: 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3',
  4: 'grid-cols-2 md:grid-cols-4',
}

export function GridContainer({
  section,
  onAction,
  tenantSlug,
  showTypeLabels,
}: {
  section: Section
  onAction?: (action: DispatchedAction) => void
  tenantSlug?: string
  showTypeLabels?: boolean
}) {
  const columns = Number(section.settings.columns) || 3
  const columnClass = COLUMN_CLASSES[columns] ?? COLUMN_CLASSES[3]
  const containerClass = resolveDesignVariantClasses(section.settings.design_variant)
  const children = section.children ?? []

  return (
    <div className={containerClass}>
      <div className={`grid gap-4 ${columnClass}`}>
        {children.length > 0
          ? renderSections(children, { onAction, tenantSlug, showTypeLabels })
          : <div className="col-span-full p-4 text-center text-sm text-current/60">Empty grid — add items.</div>}
      </div>
    </div>
  )
}
