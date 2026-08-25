import { adminApiClient } from '@/lib/api/serverApiClient'
import { TemplatesClient } from './TemplatesClient'

export default async function SuperAdminTemplatesPage() {
  const response = await adminApiClient('/api/v1/super-admin/storefront-templates')
  const templates = response.data || []

  return <TemplatesClient initialTemplates={templates} />
}
