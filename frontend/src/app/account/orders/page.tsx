import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { ApiError, serverApiClient } from '@/lib/api/serverApiClient'
import { OrdersList } from './OrdersList'
import type { Order } from '@/lib/types'

export default async function MyOrdersPage() {
  const cookieStore = await cookies()
  if (!cookieStore.get('token')?.value) {
    redirect('/login')
  }

  let initialOrders: Order[] = []
  let initialError = ''
  try {
    const data = await serverApiClient('/api/v1/customer/orders')
    initialOrders = data.data || []
  } catch (e) {
    initialError = e instanceof ApiError ? e.message : 'Failed to load orders'
  }

  return <OrdersList initialOrders={initialOrders} initialError={initialError} />
}
