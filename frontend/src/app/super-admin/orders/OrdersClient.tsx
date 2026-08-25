'use client'

import React, { useMemo, useState } from 'react'
import Link from 'next/link'
import { ShoppingCart } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { orderStatusClass, orderStatusLabel } from '@/lib/orderStatus'
import { SuperAdminPageHeader } from '../SuperAdminPageHeader'
import { formatDateTime, formatPlatformMoney, nativeSelectClass, type PlatformOrder } from '../types'
import { isUsableTenantSlug } from '@/lib/tenantSlug'

export function OrdersClient({ initialOrders }: { initialOrders: PlatformOrder[] }) {
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    return initialOrders.filter((order) => {
      if (statusFilter !== 'all' && order.status !== statusFilter) return false
      if (!q) return true
      return (
        order.order_number.toLowerCase().includes(q)
        || order.tenant_name.toLowerCase().includes(q)
        || order.tenant_slug.toLowerCase().includes(q)
      )
    })
  }, [initialOrders, query, statusFilter])

  const statuses = Array.from(new Set(initialOrders.map((o) => o.status)))

  return (
    <div className="space-y-6">
      <SuperAdminPageHeader
        title="Platform orders"
        description="Every store and marketplace sub-order. Fulfillment stays with the vendor admin."
      />
      <div className="flex flex-wrap gap-3">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search order or store"
          className="max-w-sm"
        />
        <select className={nativeSelectClass} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="all">All statuses</option>
          {statuses.map((status) => (
            <option key={status} value={status}>{orderStatusLabel[status] || status}</option>
          ))}
        </select>
      </div>
      <Card className="overflow-hidden py-0 shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Order</TableHead>
              <TableHead>Store</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Placed</TableHead>
              <TableHead className="text-end tabular-nums">Commission</TableHead>
              <TableHead className="text-end tabular-nums">Vendor net</TableHead>
              <TableHead className="text-end tabular-nums">Total</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visible.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="py-12 text-center text-muted-foreground">
                  <ShoppingCart className="mx-auto mb-2 h-8 w-8 opacity-40" />
                  No orders match this filter.
                </TableCell>
              </TableRow>
            )}
            {visible.map((order) => (
              <TableRow key={order.id} className="hover:bg-muted/50">
                <TableCell className="font-semibold">{order.order_number}</TableCell>
                <TableCell>
                  {isUsableTenantSlug(order.tenant_slug) ? (
                    <Link href={`/store/${order.tenant_slug}`} prefetch={false} className="text-primary hover:underline">
                      {order.tenant_name}
                    </Link>
                  ) : (
                    order.tenant_name
                  )}
                </TableCell>
                <TableCell>
                  <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${orderStatusClass[order.status] || ''}`}>
                    {orderStatusLabel[order.status] || order.status}
                  </span>
                </TableCell>
                <TableCell className="text-muted-foreground">{formatDateTime(order.created_at)}</TableCell>
                <TableCell className="text-end tabular-nums">{formatPlatformMoney(order.platform_commission)}</TableCell>
                <TableCell className="text-end tabular-nums">{formatPlatformMoney(order.vendor_net_payout)}</TableCell>
                <TableCell className="text-end font-medium tabular-nums">{formatPlatformMoney(order.total_amount)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
