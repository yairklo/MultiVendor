'use client'

import React, { useState } from 'react'
import { useCoupons } from '@/hooks/useCoupons'
import { useToast } from '@/context/ToastContext'
import { useConfirm } from '@/context/ConfirmContext'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import * as z from 'zod'

import { Button } from '@/components/ui/button'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
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

const formSchema = z.object({
  code: z.string().min(3, 'At least 3 characters').max(20).regex(/^[A-Za-z0-9]+$/, 'Alphanumeric only'),
  discount_type: z.enum(['percentage', 'fixed']),
  discount_val: z.coerce.number().gt(0, 'Must be positive'),
  min_order_amt: z.coerce.number().min(0, 'Cannot be negative'),
  usage_limit: z.coerce.number().gt(0, 'Must be positive'),
  valid_until: z.string().min(1, 'Required'),
})

export function CouponsPageClient({ initialCoupons }: { initialCoupons: any[] }) {
  const { fetchCoupons, createCoupon, deleteCoupon } = useCoupons()
  const { formatCurrency } = useCurrency()
  const { t } = useUiLocale()
  const { showToast } = useToast()
  const { confirm } = useConfirm()
  const [coupons, setCoupons] = useState<any[]>(initialCoupons)
  const [loading, setLoading] = useState(false)

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      code: '',
      discount_type: 'percentage',
      discount_val: 10,
      min_order_amt: 0,
      usage_limit: 100,
      valid_until: '',
    },
  })

  const loadCoupons = async () => {
    const data = await fetchCoupons()
    setCoupons(data)
  }

  const onSubmit = async (values: z.infer<typeof formSchema>) => {
    setLoading(true)
    try {
      await createCoupon({
        code: values.code.toUpperCase(),
        discount_type: values.discount_type,
        discount_val: values.discount_val,
        min_order_amt: values.min_order_amt,
        usage_limit: values.usage_limit,
        valid_until: new Date(values.valid_until).toISOString(),
      })
      form.reset()
      await loadCoupons()
      showToast(t('coupons.created'), 'success')
    } catch (error: any) {
      showToast(error.message || t('coupons.createFailed'), 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    const ok = await confirm({
      title: t('coupons.deleteConfirm'),
      confirmLabel: t('common.delete'),
      variant: 'destructive',
    })
    if (!ok) return
    try {
      await deleteCoupon(id)
      await loadCoupons()
      showToast(t('coupons.deleted'), 'success')
    } catch (error: any) {
      showToast(error.message || t('coupons.deleteFailed'), 'error')
    }
  }

  return (
    <div className="max-w-5xl">
        <h1 className="font-heading text-3xl font-bold mb-8 text-foreground">{t('coupons.title')}</h1>

      <div className="bg-card p-6 rounded-xl shadow-sm border border-border mb-8">
        <h2 className="text-xl font-bold mb-4 text-foreground">{t('coupons.create')}</h2>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <FormField
                control={form.control}
                name="code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('coupons.code')}</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. SUMMER10" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="discount_type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('coupons.discountType')}</FormLabel>
                    <FormControl>
                      <select
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                        {...field}
                      >
                        <option value="percentage">{t('coupons.percentage')}</option>
                        <option value="fixed">{t('coupons.fixed')}</option>
                      </select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="discount_val"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('coupons.discountValue')}</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.01" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <FormField
                control={form.control}
                name="min_order_amt"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('coupons.minOrder')}</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.01" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="usage_limit"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('coupons.usageLimit')}</FormLabel>
                    <FormControl>
                      <Input type="number" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="valid_until"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('coupons.validUntil')}</FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <Button type="submit" disabled={loading}>
              {loading ? t('common.creating') : t('coupons.createButton')}
            </Button>
          </form>
        </Form>
      </div>

      <div className="bg-card rounded-xl shadow-sm border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('coupons.code')}</TableHead>
              <TableHead>{t('coupons.discount')}</TableHead>
              <TableHead>{t('coupons.used')}</TableHead>
              <TableHead>{t('coupons.validUntil')}</TableHead>
              <TableHead className="text-right">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {coupons.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                  {t('coupons.none')}
                </TableCell>
              </TableRow>
            )}
            {coupons.map((coupon) => (
              <TableRow key={coupon.id} className="hover:bg-muted/50 transition-colors">
                <TableCell className="font-mono font-medium">{coupon.code}</TableCell>
                <TableCell>
                  {coupon.discount_type === 'percentage' ? `${coupon.discount_val}%` : formatCurrency(coupon.discount_val)}
                </TableCell>
                <TableCell>{coupon.used_count}</TableCell>
                <TableCell>{new Date(coupon.valid_until).toLocaleDateString()}</TableCell>
                <TableCell className="text-right">
                  <Button variant="destructive" size="sm" onClick={() => handleDelete(coupon.id)}>
                    {t('common.delete')}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
