import { Section } from '@/lib/ai/types'
import { resolveDesignVariantClasses } from '@/lib/design-tokens'
import { renderSections } from '../PageRenderer'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'
import { translate } from '@/lib/ui-i18n/translate'
import { he } from '@/lib/ui-i18n/he'
import { en } from '@/lib/ui-i18n/en'
import React from 'react'

const COLUMN_CLASSES: Record<number, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-1 sm:grid-cols-2',
  3: 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3',
  4: 'grid-cols-2 md:grid-cols-4',
}

const dictionaries = { he, en } as const

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
  
  const { lang } = useStorefrontTheme()
  const currentLang = (lang === 'he' || lang === 'en') ? lang : 'en'
  const t = (key: string) => translate(dictionaries[currentLang], key)

  const isBento = section.settings.bento_grid === true
  
  const renderedChildren = renderSections(children, { onAction, tenantSlug, showTypeLabels })

  return (
    <div className={containerClass}>
      <div className={`grid gap-4 ${isBento ? 'auto-rows-[minmax(180px,auto)] grid-flow-dense' : ''} ${columnClass}`}>
        {children.length > 0
          ? renderedChildren.map((childElement, idx) => {
              let bentoClass = ''
              if (isBento) {
                if (columns === 3) {
                  bentoClass = idx % 5 === 0 ? 'md:col-span-2 md:row-span-2' : ''
                } else if (columns === 4) {
                  bentoClass = idx % 5 === 0 || idx % 5 === 3 ? 'md:col-span-2 md:row-span-2' : ''
                }
              }
              if (!bentoClass) return childElement
              return React.cloneElement(childElement, {
                className: `${childElement.props.className} ${bentoClass}`
              })
            })
          : <div className="col-span-full p-4 text-center text-sm text-current/60">{t('common.emptyGrid')}</div>}
      </div>
    </div>
  )
}
