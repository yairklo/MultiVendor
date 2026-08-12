import { getServerTenantSlug, serverApiClient } from '@/lib/api/serverApiClient'
import { ApiError } from '@/lib/api/apiClient'
import { redirect } from 'next/navigation'
import { SettingsPageClient } from './SettingsPageClient'

export default async function SettingsPage() {
  const tenantSlug = await getServerTenantSlug()

  let initialSettings = { currency: 'USD', primary_color: '#3b82f6', default_language: 'en' }
  try {
    // The public /config endpoint (not /admin/store/...) — same call the
    // original client code made, so no session to expire here.
    const config = await serverApiClient(`/api/v1/store/${tenantSlug}/config`)
    initialSettings = {
      currency: config.currency ?? 'USD',
      primary_color: config.primary_color ?? '#3b82f6',
      default_language: config.default_language ?? 'en',
    }
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/admin/login')
    console.error('Failed to load current store settings', e)
  }

  return <SettingsPageClient initialSettings={initialSettings} />
}
