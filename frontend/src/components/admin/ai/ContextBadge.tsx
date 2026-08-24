import { PageType, StorePageSummary } from '@/lib/ai/types'

export function ContextBadge({
  targets,
  pageKey,
  pageType,
  provider,
  onChange,
}: {
  targets: StorePageSummary[]
  pageKey: string
  pageType: PageType
  provider: 'gemini' | 'mock' | null
  onChange: (pageKey: string, pageType: PageType) => void
}) {
  const current = targets.find((t) => t.page_key === pageKey && t.page_type === pageType)

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card p-4 shadow-sm">
      <span className="text-sm font-medium text-muted-foreground">Editing</span>
      <select
        className="rounded-lg border border-border px-3 py-1.5 text-sm outline-none transition-colors focus:ring-2 focus:ring-ring"
        value={`${pageType}:${pageKey}`}
        onChange={(e) => {
          const [tt, pk] = e.target.value.split(':')
          onChange(pk, tt as PageType)
        }}
      >
        <option value={`${pageType}:${pageKey}`}>
          {current ? `${current.title} (${current.page_type})` : `${pageKey} (${pageType}) — new`}
        </option>
        {targets
          .filter((t) => !(t.page_key === pageKey && t.page_type === pageType))
          .map((t) => (
            <option key={`${t.page_type}:${t.page_key}`} value={`${t.page_type}:${t.page_key}`}>
              {t.title} ({t.page_type})
            </option>
          ))}
      </select>
      {current && (
        <span className="text-xs text-muted-foreground">
          page_key=<code className="rounded bg-muted px-1 py-0.5">{current.page_key}</code> · {current.section_count} sections
        </span>
      )}
      <div className="ml-auto flex items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">Provider</span>
        {provider ? (
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
              provider === 'gemini' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
            }`}
          >
            {provider === 'gemini' ? 'Gemini live' : 'Mock mode'}
          </span>
        ) : (
          <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">…</span>
        )}
      </div>
    </div>
  )
}
