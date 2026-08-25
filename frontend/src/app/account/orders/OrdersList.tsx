'use client'

import React, { useState } from 'react'
import { useOrders } from '@/hooks/useOrders'
import { orderStatusClass as statusClass, orderStatusLabel as statusLabel } from '@/lib/orderStatus'
import { useToast } from '@/context/ToastContext'
import { useConfirm } from '@/context/ConfirmContext'
import { useCurrency } from '@/hooks/useCurrency'
import { useUiLocale } from '@/context/UiLocaleContext'

export function OrdersList({ initialOrders, initialError }: { initialOrders: any[]; initialError: string }) {
  const { fetchOrders, cancelOrder, payOrder } = useOrders()
  const { formatCurrency } = useCurrency()
  const { t } = useUiLocale()
  const { showToast } = useToast()
  const { confirm } = useConfirm()
  const [orders, setOrders] = useState<any[]>(initialOrders)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [error, setError] = useState(initialError)

  const loadOrders = async () => {
    try {
      const data = await fetchOrders()
      setOrders(data)
    } catch (e: any) {
      setError(e.message || t('orders.loadFailed'))
    }
  }

  const handlePay = async (orderId: number) => {
    setBusyId(orderId)
    setError('')
    try {
      await payOrder(orderId)
      await loadOrders()
      showToast(t('orders.paymentSuccess'), 'success')
    } catch (e: any) {
      showToast(e.message || t('orders.paymentFailed'), 'error')
    } finally {
      setBusyId(null)
    }
  }

  const handleCancel = async (orderId: number) => {
    const ok = await confirm({
      title: t('account.cancelConfirm'),
      confirmLabel: t('orders.cancelOrder'),
      cancelLabel: t('account.keepOrder'),
      variant: 'destructive',
    })
    if (!ok) return
    setBusyId(orderId)
    setError('')
    try {
      await cancelOrder(orderId)
      await loadOrders()
      showToast(t('account.cancelled'), 'success')
    } catch (e: any) {
      showToast(e.message || t('account.cancelFailed'), 'error')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-background min-h-screen text-foreground">
      <h1 className="text-3xl font-bold mb-8 border-b border-border pb-4 font-heading">{t('account.myOrders')}</h1>

      {error && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100">{error}</div>
      )}

      {orders.length === 0 ? (
        <div className="bg-card p-8 rounded-xl shadow-sm border border-border text-center text-muted-foreground">
          {t('account.none')}
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map(order => {
            const canPay = order.status === 'pending_payment'
            const canCancel = order.status === 'pending' || order.status === 'pending_payment'
            return (
              <div
                key={order.id}
                data-testid="order-card"
                className="bg-card p-6 rounded-xl shadow-sm border border-border transition-shadow duration-200 hover:shadow-md"
              >
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div className="font-bold">#{order.order_number}</div>
                    <div className="text-sm text-muted-foreground">{new Date(order.created_at).toLocaleString()}</div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${statusClass[order.status] || 'bg-muted text-muted-foreground'}`}>
                    {statusLabel[order.status] ? t(`orderStatus.${order.status}`) : order.status}
                  </span>
                </div>

                <div className="space-y-1 mb-3 text-sm text-foreground/80">
                  {order.items?.map((item: any) => (
                    <div key={item.id} className="flex justify-between">
                      <span>{item.product_name} &times; {item.quantity}</span>
                      <span>{formatCurrency(Number(item.unit_price * item.quantity))}</span>
                    </div>
                  ))}
                </div>

                <div className="flex justify-between items-center border-t border-border pt-3">
                  <span className="font-bold">{t('account.total', { amount: formatCurrency(Number(order.total_amount)) })}</span>
                  <div className="flex gap-2">
                    {canCancel && (
                      <button
                        onClick={() => handleCancel(order.id)}
                        disabled={busyId === order.id}
                        className="px-4 py-2 text-destructive border border-destructive/30 rounded-lg font-medium transition-colors duration-150 hover:bg-destructive/10 active:scale-[0.98] disabled:opacity-50"
                      >
                        {t('common.cancel')}
                      </button>
                    )}
                    {canPay && (
                      <button
                        onClick={() => handlePay(order.id)}
                        disabled={busyId === order.id}
                        className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium transition-colors duration-150 hover:bg-primary/90 active:scale-[0.98] disabled:opacity-50"
                      >
                        {busyId === order.id ? t('checkout.processing') : t('orders.pay')}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
