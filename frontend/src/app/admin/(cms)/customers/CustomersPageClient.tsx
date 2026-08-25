'use client'

import React from 'react'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useCurrency } from '@/hooks/useCurrency'
import { useUiLocale } from '@/context/UiLocaleContext'
import { formatUiDate } from '@/lib/utils'

export function CustomersPageClient({ initialCustomers }: { initialCustomers: any[] }) {
  const { formatCurrency } = useCurrency()
  const { t, locale } = useUiLocale()
  const customers = initialCustomers

  return (
    <div>
      <h1 className="font-heading text-3xl font-bold text-foreground mb-8">{t('customers.title')}</h1>

      <div className="min-w-0 overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('customers.customer')}</TableHead>
              <TableHead>{t('customers.joined')}</TableHead>
              <TableHead>{t('customers.orders')}</TableHead>
              <TableHead className="text-end">{t('customers.totalSpent')}</TableHead>
              <TableHead>{t('customers.lastOrder')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {customers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">{t('customers.none')}</TableCell>
              </TableRow>
            ) : (
              customers.map(customer => (
                <TableRow key={customer.id} className="hover:bg-muted/50 transition-colors">
                  <TableCell>
                    <div className="font-bold">{customer.full_name}</div>
                    <div className="text-sm text-muted-foreground">{customer.email}</div>
                  </TableCell>
                  <TableCell>{formatUiDate(customer.created_at, locale)}</TableCell>
                  <TableCell>{customer.orders_count}</TableCell>
                  <TableCell className="text-end font-medium tabular-nums">{formatCurrency(Number(customer.total_spent))}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatUiDate(customer.last_order_at, locale)}
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
