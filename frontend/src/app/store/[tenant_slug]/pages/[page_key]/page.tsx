import Link from 'next/link'
import { ApiError, getTenantPage } from '@/lib/api/serverApiClient'
import { DynamicPageView } from '@/components/storefront/DynamicPageView'

export default async function StorefrontDynamicPage({
  params,
}: {
  params: Promise<{ tenant_slug: string; page_key: string }>
}) {
  const { tenant_slug: tenantSlug, page_key: pageKey } = await params

  let page
  try {
    page = await getTenantPage(tenantSlug, pageKey)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-gray-50 text-center">
          <h1 className="text-xl font-bold text-gray-900">Page not found</h1>
          <p className="text-gray-500">This store has no page called &ldquo;{pageKey}&rdquo;.</p>
          <Link href={`/store/${tenantSlug}`} className="font-medium text-blue-600 hover:underline">
            Back to store
          </Link>
        </div>
      )
    }
    throw e
  }
  return <DynamicPageView page={page} tenantSlug={tenantSlug} />
}
