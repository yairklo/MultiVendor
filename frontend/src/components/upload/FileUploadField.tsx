'use client'

import React, { useRef, useState } from 'react'
import { FileText } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { useUploads } from '@/hooks/useUploads'
import { ApiError } from '@/lib/api/apiClient'
import { fileLabelFromUrl } from '@/lib/digitalFileUrl'
import { useUiLocale } from '@/context/UiLocaleContext'

interface FileUploadFieldProps {
  value: string
  onChange: (url: string) => void
  label?: string
  hint?: string
  id?: string
}

export function FileUploadField({
  value,
  onChange,
  label,
  hint,
  id = 'digital-file-upload',
}: FileUploadFieldProps) {
  const { uploadFile } = useUploads()
  const { t } = useUiLocale()
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const displayLabel = label ?? t('products.uploadFile')
  const fileLabel = fileLabelFromUrl(value)

  const handleFile = async (file: File) => {
    setError(null)
    setIsUploading(true)
    try {
      const { url } = await uploadFile(file)
      onChange(url)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.uploadFailed'))
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div>
      <Label htmlFor={id}>{displayLabel}</Label>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setIsDragOver(false)
          const file = e.dataTransfer.files?.[0]
          if (file) handleFile(file)
        }}
        onClick={() => inputRef.current?.click()}
        className={`mt-1 flex cursor-pointer items-center gap-4 rounded-lg border border-dashed p-4 transition-colors duration-150 ${
          isDragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
        }`}
      >
        <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-md border border-border bg-muted text-muted-foreground">
          <FileText className="h-7 w-7" aria-hidden />
        </div>
        <div className="min-w-0 flex-1 text-sm">
          {isUploading ? (
            <p className="text-muted-foreground">{t('upload.uploading')}</p>
          ) : fileLabel ? (
            <div className="flex items-center gap-3">
              <div className="min-w-0">
                <p className="truncate font-medium text-foreground">{fileLabel}</p>
                <p className="text-muted-foreground">{t('upload.fileAttached')}</p>
              </div>
              <button
                type="button"
                className="shrink-0 text-sm font-medium text-destructive underline-offset-4 transition-colors duration-150 hover:underline"
                onClick={(e) => {
                  e.stopPropagation()
                  onChange('')
                }}
              >
                {t('upload.removeFile')}
              </button>
            </div>
          ) : (
            <p className="text-muted-foreground">{t('upload.dropFileHint')}</p>
          )}
        </div>
        <input
          ref={inputRef}
          id={id}
          type="file"
          accept=".pdf,.zip,.epub,.docx,application/pdf,application/zip,application/epub+zip,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) handleFile(file)
            e.target.value = ''
          }}
        />
      </div>
      {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
    </div>
  )
}
