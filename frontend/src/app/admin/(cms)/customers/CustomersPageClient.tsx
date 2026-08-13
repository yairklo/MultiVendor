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

export function CustomersPageClient({ initialCustomers }: { initialCustomers: any[] }) {
  const { formatCurrency } = useCurrency()
  const customers = initialCustomers

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Customers</h1>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Customer</TableHead>
              <TableHead>Joined</TableHead>
              <TableHead>Orders</TableHead>
              <TableHead>Total Spent</TableHead>
              <TableHead>Last Order</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {customers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-gray-500">No customers yet.</TableCell>
              </TableRow>
            ) : (
              customers.map(customer => (
                <TableRow key={customer.id}>
                  <TableCell>
                    <div className="font-bold">{customer.full_name}</div>
                    <div className="text-sm text-gray-500">{customer.email}</div>
                  </TableCell>
                  <TableCell>{new Date(customer.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>{customer.orders_count}</TableCell>
                  <TableCell className="font-medium">{formatCurrency(Number(customer.total_spent))}</TableCell>
                  <TableCell className="text-gray-500">
                    {customer.last_order_at ? new Date(customer.last_order_at).toLocaleDateString() : '—'}
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
