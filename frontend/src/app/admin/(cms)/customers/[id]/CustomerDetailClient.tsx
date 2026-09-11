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
import { formatUiDate, formatUiDateTime } from '@/lib/utils'
import type { Customer, Order } from '@/lib/types'

export function CustomerDetailClient({ customer, orders }: { customer: Customer; orders: Order[] }) {
  const { formatCurrency } = useCurrency()
  const { t, locale } = useUiLocale()

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center gap-4 mb-8">
        <Link href="/admin/customers" className={buttonVariants({ variant: 'ghost' })}>
          &larr; {t('customers.backToCustomers')}
        </Link>
      </div>

      <div className="mb-6">
        <h1 className="font-heading text-3xl font-bold text-foreground">{customer.full_name}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{customer.email}</p>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-8 md:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">{t('customers.joined')}</p>
          <p className="mt-1 font-heading text-lg text-foreground">{formatUiDate(customer.created_at, locale)}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">{t('customers.orders')}</p>
          <p className="mt-1 font-heading text-lg text-foreground tabular-nums">{customer.orders_count}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">{t('customers.totalSpent')}</p>
          <p className="mt-1 font-heading text-lg text-foreground tabular-nums">{formatCurrency(Number(customer.total_spent))}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">{t('customers.lastOrder')}</p>
          <p className="mt-1 font-heading text-lg text-foreground">{formatUiDate(customer.last_order_at, locale)}</p>
        </div>
      </div>

      <h2 className="mb-3 font-heading text-xl font-medium text-foreground">{t('customers.orderHistory')}</h2>
      <div className="min-w-0 overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('orders.orderId')}</TableHead>
              <TableHead>{t('common.status')}</TableHead>
              <TableHead className="text-end">{t('orders.total')}</TableHead>
              <TableHead className="text-end">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {orders.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">{t('customers.noOrdersForCustomer')}</TableCell>
              </TableRow>
            ) : (
              orders.map(order => (
                <TableRow key={order.id} className="hover:bg-muted/50 transition-colors">
                  <TableCell>
                    <div className="font-medium">#{order.order_number}</div>
                    <div className="text-xs text-muted-foreground">{formatUiDateTime(order.created_at, locale)}</div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={orderStatusClass[order.status] || 'bg-muted text-muted-foreground'}>
                      {orderStatusLabel[order.status] ? t(`orderStatus.${order.status}`) : order.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-end tabular-nums">{formatCurrency(Number(order.total_amount))}</TableCell>
                  <TableCell className="text-end whitespace-nowrap">
                    <Link
                      href={`/admin/orders/${order.id}`}
                      className={buttonVariants({ variant: 'ghost', size: 'sm' })}
                    >
                      {t('common.view')}
                    </Link>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
