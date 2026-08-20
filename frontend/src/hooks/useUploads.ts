import { apiClient, ApiError } from '@/lib/api/apiClient'
import { getCookie } from 'cookies-next'

export interface ImportRowPreview {
  row_number: number
  data: Record<string, unknown>
  errors: string[]
}

export interface ImportPreviewResult {
  rows: ImportRowPreview[]
  valid_count: number
  total_count: number
}

export interface ImportRowOutcome {
  row_number: number
  sku?: string | null
  error?: string | null
  product_id?: number | null
  variant_id?: number | null
}

export interface ImportSummary {
  created_count: number
  updated_count: number
  failed_count: number
  created: ImportRowOutcome[]
  updated: ImportRowOutcome[]
  failed: ImportRowOutcome[]
}

export function useUploads() {
  const tenantSlug = getCookie('tenantSlug') || 'test-tenant'

  const uploadImage = async (file: File): Promise<{ url: string }> => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient(`/api/v1/admin/store/${tenantSlug}/uploads/image`, {
      method: 'POST',
      body: formData,
    })
  }

  const previewProductsImport = async (file: File): Promise<ImportPreviewResult> => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient(`/api/v1/admin/store/${tenantSlug}/products/import/preview`, {
      method: 'POST',
      body: formData,
    })
  }

  const commitProductsImport = async (rows: ImportRowPreview[]): Promise<ImportSummary> => {
    return apiClient(`/api/v1/admin/store/${tenantSlug}/products/import/commit`, {
      method: 'POST',
      body: JSON.stringify({ rows }),
    })
  }

  // The template endpoint is admin-gated (auth is a Bearer token we attach
  // ourselves, not a cookie the browser sends automatically), so a plain
  // <a href> can't reach it -- fetch it with the token and trigger a
  // client-side download instead.
  const downloadImportTemplate = async (): Promise<void> => {
    const token = getCookie('token')
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
    const response = await fetch(`${apiBase}/api/v1/admin/store/${tenantSlug}/products/import/template`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!response.ok) {
      throw new ApiError(response.status, `Failed to download template (HTTP ${response.status})`)
    }
    const blob = await response.blob()
    const blobUrl = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = 'product_import_template.xlsx'
    link.click()
    URL.revokeObjectURL(blobUrl)
  }

  return { uploadImage, previewProductsImport, commitProductsImport, downloadImportTemplate }
}
