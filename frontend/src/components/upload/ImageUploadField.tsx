'use client'

import React, { useRef, useState } from 'react'
import { Label } from '@/components/ui/label'
import { useUploads } from '@/hooks/useUploads'
import { ApiError } from '@/lib/api/apiClient'
import { resolveImageUrl } from '@/lib/media'
import { useUiLocale } from '@/context/UiLocaleContext'

interface ImageUploadFieldProps {
  value: string
  onChange: (url: string) => void
  label?: string
  id?: string
  hint?: string
  allowUrlInput?: boolean
}

/** Uploads an image file or accepts an image URL, with preview and remove capabilities. */
export function ImageUploadField({
  value,
  onChange,
  label,
  id = 'image-upload-file',
  hint,
  allowUrlInput = false,
}: ImageUploadFieldProps) {
  const { uploadImage } = useUploads()
  const { t } = useUiLocale()
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [mode, setMode] = useState<'upload' | 'url'>(
    value && (value.startsWith('http://') || value.startsWith('https://')) ? 'url' : 'upload'
  )
  const inputRef = useRef<HTMLInputElement>(null)
  const displayLabel = label ?? t('products.uploadImage')

  const handleFile = async (file: File) => {
    setError(null)
    setIsUploading(true)
    try {
      const { url } = await uploadImage(file)
      onChange(url)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.uploadFailed'))
    } finally {
      setIsUploading(false)
    }
  }

  const isExternalUrl = value.startsWith('http://') || value.startsWith('https://')

  return (
    <div>
      <div className="flex items-center justify-between">
        <Label htmlFor={id}>{displayLabel}</Label>
        {allowUrlInput && (
          <div className="flex items-center gap-1 rounded-lg border border-border bg-muted/40 p-0.5 text-xs font-medium">
            <button
              type="button"
              onClick={() => setMode('upload')}
              className={`rounded-md px-2.5 py-1 transition-colors ${
                mode === 'upload'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {t('upload.uploadTab')}
            </button>
            <button
              type="button"
              onClick={() => setMode('url')}
              className={`rounded-md px-2.5 py-1 transition-colors ${
                mode === 'url'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {t('upload.urlTab')}
            </button>
          </div>
        )}
      </div>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}

      {allowUrlInput && mode === 'url' ? (
        <div className="mt-2 space-y-3">
          <div className="flex items-center gap-3">
            <input
              type="text"
              placeholder={t('upload.pasteUrlPlaceholder')}
              className="w-full rounded-lg border border-input bg-background px-4 py-2 text-sm focus:ring-2 focus:ring-ring"
              value={isExternalUrl ? value : ''}
              onChange={(e) => {
                setError(null)
                onChange(e.target.value)
              }}
            />
            {value && isExternalUrl && (
              <button
                type="button"
                className="shrink-0 text-sm font-medium text-destructive underline-offset-4 hover:underline"
                onClick={() => onChange('')}
              >
                {t('upload.removeFile')}
              </button>
            )}
          </div>
          {value && isExternalUrl && (
            <div className="flex items-center gap-4 rounded-lg border border-border p-3">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={resolveImageUrl(value)}
                alt=""
                className="h-16 w-16 rounded-md border border-border object-cover"
                onError={() => setError(t('common.uploadFailed'))}
              />
              <div className="min-w-0 flex-1 text-xs text-muted-foreground">
                <p className="truncate font-medium text-foreground">{value}</p>
                <p>{t('upload.fileAttached')}</p>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setIsDragOver(true)
          }}
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
          {value ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={resolveImageUrl(value)}
              alt=""
              className="h-16 w-16 rounded-md border border-border object-cover"
            />
          ) : (
            <div className="flex h-16 w-16 items-center justify-center rounded-md bg-muted text-xs text-muted-foreground">
              {t('upload.noImage')}
            </div>
          )}
          <div className="min-w-0 flex-1 text-sm text-muted-foreground">
            {isUploading ? (
              <p>{t('upload.uploading')}</p>
            ) : value ? (
              <div className="flex items-center gap-3">
                <div className="min-w-0">
                  <p className="font-medium text-foreground">{t('upload.fileAttached')}</p>
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
              <p>{t('upload.dropHint')}</p>
            )}
          </div>
          <input
            ref={inputRef}
            id={id}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) handleFile(file)
              e.target.value = ''
            }}
          />
        </div>
      )}
      {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
    </div>
  )
}
