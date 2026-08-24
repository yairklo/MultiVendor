import { CSSProperties } from 'react'
import { Section } from '@/lib/ai/types'
import { resolveI18nText } from '@/lib/i18n-text'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'

export function TableSection({ section, themeStyle }: { section: Section; themeStyle: CSSProperties }) {
  const { lang } = useStorefrontTheme()
  const headers: unknown[] = Array.isArray(section.settings.headers) ? section.settings.headers : []
  const rows: unknown[][] = Array.isArray(section.settings.rows) ? section.settings.rows : []
  const title = resolveI18nText(section.settings.title, lang)

  return (
    <div
      className="rounded-2xl p-6"
      style={{ ...themeStyle, background: 'var(--section-bg, #ffffff)', color: 'var(--section-text, #111827)' }}
    >
      {title && <h2 className="mb-3 text-xl font-bold">{title}</h2>}
      {headers.length === 0 ? (
        <span className="text-sm text-gray-400">No table data configured.</span>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-100">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50">
              <tr>
                {headers.map((h, i) => (
                  <th key={i} className="px-4 py-2 font-semibold text-gray-700">
                    {resolveI18nText(h, lang)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((row, i) => (
                <tr key={i} className="transition-colors hover:bg-gray-50">
                  {headers.map((_, j) => (
                    <td key={j} className="px-4 py-2 text-gray-600">
                      {resolveI18nText(row?.[j], lang)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
