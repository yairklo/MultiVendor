import Link from 'next/link'
import { adminApiClient } from '@/lib/api/serverApiClient'
import { SuperAdminClient } from './SuperAdminClient'

// Unauthenticated requests never reach this page — proxy.ts middleware
// (matcher `/super-admin/:path*`) redirects to /admin/login before render.
export default async function SuperAdminPage() {
  const response = await adminApiClient('/api/v1/super-admin/tenants')
  const tenants = response.data || []

  return (
    <>
      <div className="flex justify-end bg-muted/30 px-8 pt-6">
        <Link
          href="/super-admin/templates"
          className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm font-semibold text-foreground shadow-sm transition-all duration-150 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.98]"
        >
          Storefront templates
        </Link>
      </div>
      <SuperAdminClient initialTenants={tenants} />
    </>
  )
}
