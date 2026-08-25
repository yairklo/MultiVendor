'use client'

import React, { useState } from 'react'
import { apiClient } from '@/lib/api/apiClient'
import { getCookie } from 'cookies-next'
import { orderStatusClass, orderStatusLabel } from '@/lib/orderStatus'
import { useToast } from '@/context/ToastContext'
import { useCurrency } from '@/hooks/useCurrency'
import { useTenantSlug } from '@/hooks/useTenantSlug'
import { useUiLocale } from '@/context/UiLocaleContext'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

// No real order is ever in plain 'pending' — checkout always creates
// 'pending_payment', which becomes 'processing' once paid. 'pending' was a
// leftover from before that flow existed and isn't a reachable admin action.
const MANUAL_STATUSES = ['processing', 'completed', 'cancelled']

export function OrdersPageClient({ initialOrders }: { initialOrders: any[] }) {
  const { showToast } = useToast()
  const { formatCurrency } = useCurrency()
  const [orders, setOrders] = useState<any[]>(initialOrders)
  const [exporting, setExporting] = useState(false)
  const [updatingId, setUpdatingId] = useState<number | null>(null)
  const tenantSlug = useTenantSlug()
  const { t } = useUiLocale()

  const fetchOrders = async () => {
    if (!tenantSlug) return
    try {
      const data = await apiClient(`/api/v1/admin/store/${tenantSlug}/orders`)
      setOrders(data.items || data || [])
    } catch (e) {
      console.error(e)
    }
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
      const res = await fetch(`${apiBase}/api/v1/admin/store/${tenantSlug}/reports/export?report_type=orders`, {
        headers: { Authorization: `Bearer ${getCookie('token')}` },
      })
      if (!res.ok) throw new Error('Export failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'orders.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Failed to export orders CSV:', e)
      showToast(t('orders.exportFailed'), 'error')
    } finally {
      setExporting(false)
    }
  }

  const handleStatusChange = async (orderId: number, status: string) => {
    setUpdatingId(orderId)
    try {
      await apiClient(`/api/v1/admin/store/${tenantSlug}/orders/${orderId}/status?status=${status}`, {
        method: 'PATCH',
      })
      await fetchOrders()
      showToast(t('orders.statusUpdated', { id: orderId, status: t(`orderStatus.${status}`) || status }), 'success')
    } catch (e) {
      console.error('Failed to update order status:', e)
      showToast(t('orders.statusFailed'), 'error')
    } finally {
      setUpdatingId(null)
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="font-heading text-3xl font-bold text-foreground">{t('orders.title')}</h1>
        <Button onClick={handleExport} disabled={exporting} variant="default">
          {exporting ? t('orders.exporting') : t('orders.exportCsv')}
        </Button>
      </div>

      <div className="bg-card rounded-xl shadow-apple-elevated border border-border overflow-hidden relative max-h-[70vh] overflow-y-auto">
        <Table>
          <TableHeader className="sticky top-0 z-10 backdrop-blur-md bg-background/80 border-b border-border/40">
            <TableRow>
              <TableHead className="w-[120px]">{t('orders.orderId')}</TableHead>
              <TableHead>{t('orders.customer')}</TableHead>
              <TableHead>{t('orders.total')}</TableHead>
              <TableHead className="text-end">{t('common.status')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {orders.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">{t('orders.noOrders')}</TableCell>
              </TableRow>
            )}
            {orders.map(order => (
              <TableRow key={order.id} className="group hover:bg-muted/50 transition-colors duration-100 ease-spring">
                <TableCell className="font-medium tabular-nums text-muted-foreground">#{order.id}</TableCell>
                <TableCell>
                  <div className="font-medium text-foreground">{order.customer_name || t('orders.guest')}</div>
                  {order.customer_email && (
                    <div className="text-sm text-muted-foreground">{order.customer_email}</div>
                  )}
                </TableCell>
                <TableCell className="tabular-nums font-medium">{formatCurrency(Number(order.total_amount))}</TableCell>
                <TableCell className="text-end">
                  <div className="flex items-center justify-end gap-3 relative">
                    <Badge variant="outline" className={`${orderStatusClass[order.status] || 'bg-muted text-muted-foreground'}`}>
                      <div className={`h-1.5 w-1.5 rounded-full me-1.5 ${order.status === 'completed' ? 'bg-green-500' : order.status === 'cancelled' ? 'bg-red-500' : 'bg-yellow-500'}`} />
                      {orderStatusLabel[order.status] ? t(`orderStatus.${order.status}`) : order.status || t('orderStatus.pending')}
                    </Badge>
                    <div className="flex items-center justify-end">
                      <select
                        aria-label={`Change status for order ${order.id}`}
                        value={MANUAL_STATUSES.includes(order.status) ? order.status : ''}
                        disabled={updatingId === order.id}
                        onChange={e => handleStatusChange(order.id, e.target.value)}
                        className="text-xs border border-input rounded-md px-1.5 py-1 text-muted-foreground bg-background transition-colors focus:outline-none focus:ring-2 focus:ring-ring/50 disabled:opacity-50 hover:bg-muted"
                      >
                        {!MANUAL_STATUSES.includes(order.status) && (
                          <option value="" disabled>{orderStatusLabel[order.status] ? t(`orderStatus.${order.status}`) : order.status}</option>
                        )}
                        {MANUAL_STATUSES.map(s => (
                          <option key={s} value={s}>{t(`orderStatus.${s}`)}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
