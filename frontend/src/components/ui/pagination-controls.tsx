import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useUiLocale } from '@/context/UiLocaleContext'

export interface PaginationMeta {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export function PaginationControls({ meta, onPageChange }: { meta: PaginationMeta | null; onPageChange: (page: number) => void }) {
  const { t } = useUiLocale()
  if (!meta || meta.total_pages <= 1) return null

  return (
    <div className="flex items-center justify-between border-t border-border bg-muted/30 px-5 py-3">
      <span className="text-sm text-muted-foreground">
        {t('common.pagination', { total: meta.total, page: meta.page, pages: meta.total_pages })}
      </span>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(meta.page - 1)}
          disabled={meta.page <= 1}
          aria-label={t('common.previousPage')}
          className="rounded-lg border border-border p-2 text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronLeft className="h-4 w-4 rtl:rotate-180" />
        </button>
        <button
          onClick={() => onPageChange(meta.page + 1)}
          disabled={meta.page >= meta.total_pages}
          aria-label={t('common.nextPage')}
          className="rounded-lg border border-border p-2 text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronRight className="h-4 w-4 rtl:rotate-180" />
        </button>
      </div>
    </div>
  )
}
