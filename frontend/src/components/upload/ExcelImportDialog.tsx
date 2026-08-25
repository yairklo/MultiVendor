'use client'

import React, { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { ApiError } from '@/lib/api/apiClient'
import { ImportPreviewResult, ImportRowPreview, ImportSummary } from '@/hooks/useUploads'
import { useUiLocale } from '@/context/UiLocaleContext'

interface ExcelImportDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  preview: (file: File) => Promise<ImportPreviewResult>
  commit: (rows: ImportRowPreview[]) => Promise<ImportSummary>
  onDownloadTemplate?: () => void
  onImported?: () => void
}

type Step = 'select' | 'preview' | 'summary'

/**
 * Generic file->preview->commit import flow. Kept generic (preview/commit
 * passed in as props) specifically so other entities (customers, orders)
 * can reuse this without a rewrite -- only the products import is wired up
 * to real endpoints today.
 */
export function ExcelImportDialog({
  open, onOpenChange, title, preview, commit, onDownloadTemplate, onImported,
}: ExcelImportDialogProps) {
  const { t } = useUiLocale()
  const [step, setStep] = useState<Step>('select')
  const [isBusy, setIsBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [previewResult, setPreviewResult] = useState<ImportPreviewResult | null>(null)
  const [summary, setSummary] = useState<ImportSummary | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const reset = () => {
    setStep('select')
    setPreviewResult(null)
    setSummary(null)
    setError(null)
  }

  const handleFile = async (file: File) => {
    setError(null)
    setIsBusy(true)
    try {
      const result = await preview(file)
      setPreviewResult(result)
      setStep('preview')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('import.parseFailed'))
    } finally {
      setIsBusy(false)
    }
  }

  const handleConfirm = async () => {
    if (!previewResult) return
    setError(null)
    setIsBusy(true)
    try {
      const result = await commit(previewResult.rows.filter((r) => r.errors.length === 0))
      setSummary(result)
      setStep('summary')
      onImported?.()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('import.importFailed'))
    } finally {
      setIsBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => { onOpenChange(next); if (!next) reset() }}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>

        {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>}

        {step === 'select' && (
          <div className="space-y-4">
            {onDownloadTemplate && (
              <button
                type="button"
                onClick={onDownloadTemplate}
                className="text-sm text-blue-600 underline underline-offset-2"
              >
                {t('import.downloadTemplate')}
              </button>
            )}
            <div
              onClick={() => inputRef.current?.click()}
              className="cursor-pointer rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500 hover:border-gray-400"
            >
              {isBusy ? t('import.reading') : t('import.chooseFile')}
              <input
                ref={inputRef}
                type="file"
                accept=".xlsx"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) handleFile(file)
                  e.target.value = ''
                }}
              />
            </div>
          </div>
        )}

        {step === 'preview' && previewResult && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">
              {t('import.previewValid', { valid: previewResult.valid_count, total: previewResult.total_count })}
            </p>
            <div className="max-h-80 overflow-auto rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('import.row')}</TableHead>
                    <TableHead>{t('import.sku')}</TableHead>
                    <TableHead>{t('import.name')}</TableHead>
                    <TableHead>{t('import.price')}</TableHead>
                    <TableHead>{t('import.stock')}</TableHead>
                    <TableHead>{t('common.status')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {previewResult.rows.map((row) => (
                    <TableRow key={row.row_number} className={row.errors.length ? 'bg-red-50' : ''}>
                      <TableCell>{row.row_number}</TableCell>
                      <TableCell>{String(row.data.sku ?? '')}</TableCell>
                      <TableCell>{String(row.data.name_en ?? '')}</TableCell>
                      <TableCell>{String(row.data.base_price ?? '')}</TableCell>
                      <TableCell>{String(row.data.stock_quantity ?? '')}</TableCell>
                      <TableCell className="text-red-600">{row.errors.join('; ')}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}

        {step === 'summary' && summary && (
          <div className="space-y-2 text-sm">
            <p>{t('import.created')}: <strong>{summary.created_count}</strong></p>
            <p>{t('import.updated')}: <strong>{summary.updated_count}</strong></p>
            <p>{t('import.failed')}: <strong>{summary.failed_count}</strong></p>
            {summary.failed.length > 0 && (
              <ul className="max-h-40 list-disc space-y-1 overflow-auto pl-5 text-red-600">
                {summary.failed.map((f) => (
                  <li key={f.row_number}>{t('import.rowError', { row: f.row_number })}{f.sku ? ` (${f.sku})` : ''}: {f.error}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        <DialogFooter>
          {step === 'preview' && (
            <>
              <Button variant="outline" onClick={reset} disabled={isBusy}>{t('common.back')}</Button>
              <Button onClick={handleConfirm} disabled={isBusy || previewResult?.valid_count === 0}>
                {isBusy ? t('import.importing') : t('import.importRows', { count: previewResult?.valid_count ?? 0 })}
              </Button>
            </>
          )}
          {step === 'summary' && (
            <Button onClick={() => onOpenChange(false)}>{t('common.done')}</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
