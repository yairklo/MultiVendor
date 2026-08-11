import { useState } from 'react'
import { History, RotateCcw } from 'lucide-react'
import { StorePageVersionSummary } from '@/lib/ai/types'
import { parseServerDate } from '@/lib/utils'

function timeAgo(isoDate: string): string {
  const diffMs = Date.now() - parseServerDate(isoDate).getTime()
  const minutes = Math.round(diffMs / 60000)
  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  return `${days}d ago`
}

export function VersionHistoryPanel({
  versions,
  onRevert,
  revertingId,
  publishedAt,
}: {
  versions: StorePageVersionSummary[]
  onRevert: (versionId: number) => void
  revertingId: number | null
  /** When the current draft was last published — shown separately from each version's save time. */
  publishedAt?: string | null
}) {
  const [open, setOpen] = useState(false)

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50"
      >
        <History className="h-4 w-4" />
        History
        {versions.length > 0 && (
          <span className="rounded-full bg-gray-100 px-1.5 py-0.5 text-xs font-semibold text-gray-500">
            {versions.length}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-20 mt-2 w-80 rounded-xl border border-gray-100 bg-white p-2 shadow-lg">
          <div className="px-2 py-1 text-xs font-semibold uppercase tracking-wide text-gray-400">
            Version History
          </div>
          <div className="px-2 pb-2 text-xs text-gray-500">
            Last published: {publishedAt ? timeAgo(publishedAt) : 'never'}
          </div>
          {versions.length === 0 ? (
            <div className="px-2 py-3 text-sm text-gray-400">No edits to this page yet.</div>
          ) : (
            <ul className="max-h-72 overflow-y-auto">
              {versions.map((v) => (
                <li key={v.id} className="flex items-center justify-between gap-2 rounded-lg px-2 py-2 hover:bg-gray-50">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-gray-900">{v.title}</div>
                    <div className="text-xs text-gray-400">
                      Saved {timeAgo(v.created_at)} · {v.section_count} sections
                    </div>
                  </div>
                  <button
                    type="button"
                    disabled={revertingId === v.id}
                    onClick={() => onRevert(v.id)}
                    className="flex shrink-0 items-center gap-1 rounded-lg border px-2 py-1 text-xs font-semibold text-gray-600 hover:bg-gray-100 disabled:opacity-50"
                  >
                    <RotateCcw className="h-3 w-3" />
                    {revertingId === v.id ? 'Reverting…' : 'Revert'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
