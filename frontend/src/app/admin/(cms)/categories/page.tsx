import { adminApiClient, getServerTenantSlug } from '@/lib/api/serverApiClient'
import { CategoriesPageClient } from './CategoriesPageClient'

export default async function CategoriesPage() {
  const tenantSlug = await getServerTenantSlug()
  const data = await adminApiClient(`/api/v1/admin/store/${tenantSlug}/categories`)
  const categories = Array.isArray(data) ? data : (data.data || [])

  return <CategoriesPageClient initialCategories={categories} />
}
