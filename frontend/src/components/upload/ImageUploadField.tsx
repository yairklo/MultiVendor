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
}

/** Uploads a file immediately on selection and writes the returned URL into `value`/`onChange` -- the same plain string the "Image URL" field already uses, so no product schema changes were needed to support this. */
export function ImageUploadField({ value, onChange, label, id = 'image-upload-file', hint }: ImageUploadFieldProps) {
  const { uploadImage } = useUploads()
  const { t } = useUiLocale()
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
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
        {value ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={resolveImageUrl(value)} alt="" className="h-16 w-16 rounded-md border border-border object-cover" />
        ) : (
          <div className="flex h-16 w-16 items-center justify-center rounded-md bg-muted text-xs text-muted-foreground">
            {t('upload.noImage')}
          </div>
        )}
        <div className="text-sm text-muted-foreground">
          {isUploading ? t('upload.uploading') : t('upload.dropHint')}
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
      {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
    </div>
  )
}
