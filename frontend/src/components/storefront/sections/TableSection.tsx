import { CSSProperties } from 'react'
import { Section } from '@/lib/ai/types'

function cellText(cell: unknown): string {
  if (cell == null) return ''
  if (typeof cell === 'object' && 'value' in (cell as any)) return String((cell as any).value ?? '')
  return String(cell)
}

export function TableSection({ section, themeStyle }: { section: Section; themeStyle: CSSProperties }) {
  const headers: unknown[] = Array.isArray(section.settings.headers) ? section.settings.headers : []
  const rows: unknown[][] = Array.isArray(section.settings.rows) ? section.settings.rows : []

  return (
    <div
      className="rounded-2xl p-6"
      style={{ ...themeStyle, background: 'var(--section-bg, #ffffff)', color: 'var(--section-text, #111827)' }}
    >
      {section.settings.title && <h2 className="mb-3 text-xl font-bold">{section.settings.title}</h2>}
      {headers.length === 0 ? (
        <span className="text-sm text-gray-400">No table data configured.</span>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-100">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50">
              <tr>
                {headers.map((h, i) => (
                  <th key={i} className="px-4 py-2 font-semibold text-gray-700">
                    {cellText(h)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((row, i) => (
                <tr key={i}>
                  {headers.map((_, j) => (
                    <td key={j} className="px-4 py-2 text-gray-600">
                      {cellText(row?.[j])}
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
