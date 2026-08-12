import { CSSProperties } from 'react'
import { DispatchedAction, Section, StorePageSchema } from '@/lib/ai/types'
import { getSectionThemeStyle } from './theme'
import { HeroBanner } from './sections/HeroBanner'
import { ProductGrid } from './sections/ProductGrid'
import { VideoEmbed } from './sections/VideoEmbed'
import { TextBlock } from './sections/TextBlock'
import { Gallery } from './sections/Gallery'
import { ButtonGroupSection } from './sections/ButtonGroupSection'
import { TableSection } from './sections/TableSection'
import { GridContainer } from './sections/GridContainer'
import { TwoColumnLayout } from './sections/TwoColumnLayout'

export type SectionComponent = (props: {
  section: Section
  themeStyle: CSSProperties
  onAction?: (action: DispatchedAction) => void
  tenantSlug?: string
  showTypeLabels?: boolean
  onInlineEdit?: (sectionId: string, patch: Partial<Section>) => void
}) => React.JSX.Element

export type RenderSectionsOptions = {
  onAction?: (action: DispatchedAction) => void
  tenantSlug?: string
  /** Overlays each section's type as a small badge — useful in the admin editor preview, not on the live storefront. */
  showTypeLabels?: boolean
  /** Only ever supplied by the admin editor — turns the section's own text into an editable field in place. Never passed on the live storefront. */
  onInlineEdit?: (sectionId: string, patch: Partial<Section>) => void
}

const SECTION_COMPONENTS: Record<Section['type'], SectionComponent> = {
  hero_banner: HeroBanner,
  product_grid: ProductGrid,
  video_embed: VideoEmbed,
  text_block: TextBlock,
  gallery: Gallery,
  button_group: ButtonGroupSection,
  table: TableSection,
  grid_container: GridContainer,
  two_column_layout: TwoColumnLayout,
}

/**
 * Shared recursive traversal — both the top-level PageRenderer and the two container
 * components (GridContainer/TwoColumnLayout) call this for their own child sections, so
 * nesting logic lives in exactly one place rather than being reimplemented per container.
 */
export function renderSections(sections: Section[], opts: RenderSectionsOptions): React.JSX.Element[] {
  return sections.map((section) => {
    const Component = SECTION_COMPONENTS[section.type]
    if (!Component) {
      return (
        <div key={section.id} className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Unknown section type: {section.type}
        </div>
      )
    }
    return (
      <div key={section.id} className="relative">
        {opts.showTypeLabels && (
          <div className="absolute -top-2 left-4 z-10 rounded-full bg-gray-900/80 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-white">
            {section.type}
          </div>
        )}
        <Component
          section={section}
          themeStyle={getSectionThemeStyle(section.settings)}
          onAction={opts.onAction}
          tenantSlug={opts.tenantSlug}
          showTypeLabels={opts.showTypeLabels}
          onInlineEdit={opts.onInlineEdit}
        />
      </div>
    )
  })
}

export function PageRenderer({
  page,
  onAction,
  showTypeLabels = false,
  tenantSlug,
}: {
  page: StorePageSchema | null
  onAction?: (action: DispatchedAction) => void
  /** Overlays each section's type as a small badge — useful in the admin editor preview, not on the live storefront. */
  showTypeLabels?: boolean
  /** When provided, product_grid sections fetch and render real products for this store instead of placeholders. */
  tenantSlug?: string
}) {
  if (!page) {
    return <div className="p-8 text-center text-gray-400">Loading page…</div>
  }

  return (
    <div className="flex flex-col gap-4">
      {renderSections(page.sections, { onAction, tenantSlug, showTypeLabels })}
      {page.sections.length === 0 && <div className="p-8 text-center text-gray-400">No sections yet.</div>}
    </div>
  )
}
