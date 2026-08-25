import { getServerTenantSlug, serverApiClient } from '@/lib/api/serverApiClient'
import { ApiError } from '@/lib/api/apiClient'
import { redirect } from 'next/navigation'
import { SettingsPageClient } from './SettingsPageClient'

export default async function SettingsPage() {
  const tenantSlug = await getServerTenantSlug()

  let initialSettings = {
    currency: 'ILS',
    primary_color: '#000000',
    logo_url: '',
    banner_url: '',
    support_email: '',
    supported_languages: ['he'],
    default_language: 'he',
    review_moderation_enabled: false,
    allow_unverified_reviews: true,
    custom_css: '',
    template_key: '',
    nav_items: null as null,
  }
  try {
    const config = await serverApiClient(`/api/v1/store/${tenantSlug}/config`)
    initialSettings = {
      currency: config.currency ?? 'ILS',
      primary_color: config.primary_color ?? '#000000',
      logo_url: config.logo_url ?? '',
      banner_url: config.banner_url ?? '',
      support_email: config.support_email ?? '',
      supported_languages: config.supported_languages ?? ['he'],
      default_language: config.default_language ?? 'he',
      review_moderation_enabled: config.review_moderation_enabled ?? false,
      allow_unverified_reviews: config.allow_unverified_reviews ?? true,
      custom_css: config.custom_css ?? '',
      template_key: config.template_key ?? '',
      nav_items: config.nav_items ?? null,
    }
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/admin/login')
    console.error('Failed to load current store settings', e)
  }

  return <SettingsPageClient initialSettings={initialSettings} />
}
