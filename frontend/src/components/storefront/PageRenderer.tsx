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

type SectionComponent = (props: {
  section: Section
  themeStyle: CSSProperties
  onAction?: (action: DispatchedAction) => void
  tenantSlug?: string
}) => React.JSX.Element

const SECTION_COMPONENTS: Record<Section['type'], SectionComponent> = {
  hero_banner: HeroBanner,
  product_grid: ProductGrid,
  video_embed: VideoEmbed,
  text_block: TextBlock,
  gallery: Gallery,
  button_group: ButtonGroupSection,
  table: TableSection,
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
      {page.sections.map((section) => {
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
            {showTypeLabels && (
              <div className="absolute -top-2 left-4 rounded-full bg-gray-900/80 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-white">
                {section.type}
              </div>
            )}
            <Component
              section={section}
              themeStyle={getSectionThemeStyle(section.settings)}
              onAction={onAction}
              tenantSlug={tenantSlug}
            />
          </div>
        )
      })}
      {page.sections.length === 0 && <div className="p-8 text-center text-gray-400">No sections yet.</div>}
    </div>
  )
}
