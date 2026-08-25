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
    <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
      <span className="text-sm text-gray-500">
        {t('common.pagination', { total: meta.total, page: meta.page, pages: meta.total_pages })}
      </span>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(meta.page - 1)}
          disabled={meta.page <= 1}
          aria-label={t('common.previousPage')}
          className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <button
          onClick={() => onPageChange(meta.page + 1)}
          disabled={meta.page >= meta.total_pages}
          aria-label={t('common.nextPage')}
          className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
