import { Section } from '@/lib/ai/types'
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
  onAction?: (action: any) => void
  tenantSlug?: string
  showTypeLabels?: boolean
}) {
  const columns = Number(section.settings.columns) || 3
  const columnClass = COLUMN_CLASSES[columns] ?? COLUMN_CLASSES[3]
  const containerClass = resolveDesignVariantClasses(section.settings.design_variant)
  const children = section.children ?? []

  const isBento = section.settings.bento_grid === true
  
  // Bento grid mapping for auto-spans
  const renderBentoChildren = () => {
    return children.map((child, idx) => {
      let bentoClass = ''
      if (isBento) {
        if (columns === 3) {
          bentoClass = idx === 0 ? 'md:col-span-2 md:row-span-2' : ''
        } else if (columns === 4) {
          bentoClass = idx === 0 || idx === 3 ? 'md:col-span-2 md:row-span-2' : 'md:col-span-1 md:row-span-1'
        }
      }
      return (
        <div key={child.id} className={bentoClass}>
          {renderSections([child], { onAction, tenantSlug, showTypeLabels })}
        </div>
      )
    })
  }

  return (
    <div className={containerClass}>
      <div className={`grid gap-4 ${isBento ? 'auto-rows-[minmax(180px,auto)]' : ''} ${columnClass}`}>
        {children.length > 0
          ? (isBento ? renderBentoChildren() : renderSections(children, { onAction, tenantSlug, showTypeLabels }))
          : <div className="col-span-full p-4 text-center text-sm text-current/60">Empty grid — add items.</div>}
      </div>
    </div>
  )
}
