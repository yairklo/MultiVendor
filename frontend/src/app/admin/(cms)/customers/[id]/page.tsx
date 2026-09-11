import Link from 'next/link'
import { buttonVariants } from '@/components/ui/button'
import { ApiError } from '@/lib/api/apiClient'
import { adminApiClient, getServerTenantSlug } from '@/lib/api/serverApiClient'
import { CustomerDetailClient } from './CustomerDetailClient'
import type { Customer, Order } from '@/lib/types'

export default async function CustomerDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id: customerId } = await params
  const tenantSlug = await getServerTenantSlug()

  let detail: { customer: Customer; orders: Order[] } | null = null
  let error = ''
  try {
    detail = await adminApiClient(`/api/v1/admin/store/${tenantSlug}/customers/${customerId}`)
  } catch (e) {
    error = e instanceof ApiError ? e.message : 'Failed to load customer'
  }

  if (!detail) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center mb-6 gap-4">
          <Link href="/admin/customers" className={buttonVariants({ variant: 'ghost' })}>
            &larr; Back
          </Link>
          <h1 className="text-3xl font-bold text-foreground">Customer</h1>
        </div>
        <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">{error}</div>
      </div>
    )
  }

  return <CustomerDetailClient customer={detail.customer} orders={detail.orders} />
}
