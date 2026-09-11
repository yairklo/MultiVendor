import Link from 'next/link'
import { buttonVariants } from '@/components/ui/button'
import { ApiError } from '@/lib/api/apiClient'
import { adminApiClient, getServerTenantSlug } from '@/lib/api/serverApiClient'
import { OrderDetailClient } from './OrderDetailClient'
import type { Order } from '@/lib/types'

export default async function OrderDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id: orderId } = await params
  const tenantSlug = await getServerTenantSlug()

  let order: Order | null = null
  let error = ''
  try {
    order = await adminApiClient(`/api/v1/admin/store/${tenantSlug}/orders/${orderId}`)
  } catch (e) {
    error = e instanceof ApiError ? e.message : 'Failed to load order'
  }

  if (!order) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center mb-6 gap-4">
          <Link href="/admin/orders" className={buttonVariants({ variant: 'ghost' })}>
            &larr; Back
          </Link>
          <h1 className="text-3xl font-bold text-foreground">Order</h1>
        </div>
        <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">{error}</div>
      </div>
    )
  }

  return <OrderDetailClient order={order} />
}
