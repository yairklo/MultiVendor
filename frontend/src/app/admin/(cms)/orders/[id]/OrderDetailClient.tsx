'use client'

import React from 'react'
import Link from 'next/link'
import { buttonVariants } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { orderStatusClass, orderStatusLabel } from '@/lib/orderStatus'
import { useCurrency } from '@/hooks/useCurrency'
import { useUiLocale } from '@/context/UiLocaleContext'
import { formatUiDateTime } from '@/lib/utils'
import type { Order } from '@/lib/types'

export function OrderDetailClient({ order }: { order: Order }) {
  const { formatCurrency } = useCurrency()
  const { t, locale } = useUiLocale()

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center gap-4 mb-8">
        <Link href="/admin/orders" className={buttonVariants({ variant: 'ghost' })}>
          &larr; {t('orders.backToOrders')}
        </Link>
      </div>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-heading text-3xl font-bold text-foreground">{t('orders.orderDetails')} #{order.order_number}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{formatUiDateTime(order.created_at, locale)}</p>
        </div>
        <Badge variant="outline" className={orderStatusClass[order.status] || 'bg-muted text-muted-foreground'}>
          {orderStatusLabel[order.status] ? t(`orderStatus.${order.status}`) : order.status}
        </Badge>
      </div>

      <div className="rounded-xl border border-border bg-card shadow-sm p-6 mb-6">
        <p className="text-sm font-medium text-foreground">{order.customer_name || t('orders.guest')}</p>
        {order.customer_email && <p className="text-sm text-muted-foreground">{order.customer_email}</p>}
      </div>

      <div className="min-w-0 overflow-hidden rounded-xl border border-border bg-card shadow-sm mb-6">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('orders.items')}</TableHead>
              <TableHead className="text-end">{t('orders.quantity')}</TableHead>
              <TableHead className="text-end">{t('orders.total')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {order.items.map(item => (
              <TableRow key={item.id}>
                <TableCell>
                  <div className="font-medium text-foreground">{item.product_name}</div>
                  {item.sku && <div className="text-xs text-muted-foreground">{item.sku}</div>}
                </TableCell>
                <TableCell className="text-end tabular-nums">{item.quantity}</TableCell>
                <TableCell className="text-end tabular-nums">{formatCurrency(Number(item.unit_price) * item.quantity)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="rounded-xl border border-border bg-card shadow-sm p-6 space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">{t('orders.subtotal')}</span>
          <span className="tabular-nums">{formatCurrency(Number(order.subtotal))}</span>
        </div>
        {Number(order.discount_amt) > 0 && (
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">{t('orders.discount')}</span>
            <span className="tabular-nums">-{formatCurrency(Number(order.discount_amt))}</span>
          </div>
        )}
        {Number(order.shipping_fee) > 0 && (
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">{t('orders.shipping')}</span>
            <span className="tabular-nums">{formatCurrency(Number(order.shipping_fee))}</span>
          </div>
        )}
        <div className="flex justify-between font-bold border-t border-border pt-2 mt-2">
          <span>{t('orders.total')}</span>
          <span className="tabular-nums">{formatCurrency(Number(order.total_amount))}</span>
        </div>
      </div>
    </div>
  )
}
