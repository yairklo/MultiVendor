'use client'

import React, { useRef, useState } from 'react'
import { Label } from '@/components/ui/label'
import { useUploads } from '@/hooks/useUploads'
import { ApiError } from '@/lib/api/apiClient'
import { resolveImageUrl } from '@/lib/media'

interface ImageUploadFieldProps {
  value: string
  onChange: (url: string) => void
  label?: string
}

/** Uploads a file immediately on selection and writes the returned URL into `value`/`onChange` -- the same plain string the "Image URL" field already uses, so no product schema changes were needed to support this. */
export function ImageUploadField({ value, onChange, label = 'Product Image' }: ImageUploadFieldProps) {
  const { uploadImage } = useUploads()
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = async (file: File) => {
    setError(null)
    setIsUploading(true)
    try {
      const { url } = await uploadImage(file)
      onChange(url)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div>
      <Label htmlFor="product-image-file">{label}</Label>
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
        className={`mt-1 flex cursor-pointer items-center gap-4 rounded-lg border border-dashed p-4 transition-colors ${
          isDragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        {value ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={resolveImageUrl(value)} alt="Preview" className="h-16 w-16 rounded-md border border-gray-100 object-cover" />
        ) : (
          <div className="flex h-16 w-16 items-center justify-center rounded-md bg-gray-100 text-xs text-gray-400">
            No image
          </div>
        )}
        <div className="text-sm text-gray-500">
          {isUploading ? 'Uploading…' : 'Click or drag an image here (JPG, PNG, WEBP, GIF · max 5MB)'}
        </div>
        <input
          ref={inputRef}
          id="product-image-file"
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
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  )
}
