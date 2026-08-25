import { PageType, StorePageSummary } from '@/lib/ai/types'
import { useUiLocale } from '@/context/UiLocaleContext'

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
  const { t } = useUiLocale()
  const current = targets.find((target) => target.page_key === pageKey && target.page_type === pageType)

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card p-4 shadow-sm">
      <span className="text-sm font-medium text-muted-foreground">{t('aiLayout.editing')}</span>
      <select
        className="rounded-lg border border-border px-3 py-1.5 text-sm outline-none transition-colors focus:ring-2 focus:ring-ring"
        value={`${pageType}:${pageKey}`}
        onChange={(e) => {
          const [tt, pk] = e.target.value.split(':')
          onChange(pk, tt as PageType)
        }}
      >
        <option value={`${pageType}:${pageKey}`}>
          {current ? `${current.title} (${current.page_type})` : `${pageKey} (${pageType})`}
        </option>
        {targets
          .filter((target) => !(target.page_key === pageKey && target.page_type === pageType))
          .map((target) => (
            <option key={`${target.page_type}:${target.page_key}`} value={`${target.page_type}:${target.page_key}`}>
              {target.title} ({target.page_type})
            </option>
          ))}
      </select>
      {current && (
        <span className="text-xs text-muted-foreground">
          page_key=<code className="rounded bg-muted px-1 py-0.5">{current.page_key}</code> · {t('aiLayout.sectionCount', { count: current.section_count })}
        </span>
      )}
      <div className="ms-auto flex items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">{t('aiLayout.provider')}</span>
        {provider ? (
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
              provider === 'gemini' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
            }`}
          >
            {provider === 'gemini' ? t('aiLayout.geminiLive') : t('aiLayout.mockMode')}
          </span>
        ) : (
          <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">…</span>
        )}
      </div>
    </div>
  )
}
