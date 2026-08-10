'use client'

import React, { useState, useEffect } from 'react'
import { useCoupons } from '@/hooks/useCoupons'
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

const formSchema = z.object({
  code: z.string().min(3, 'At least 3 characters').max(20).regex(/^[A-Za-z0-9]+$/, 'Alphanumeric only'),
  discount_type: z.enum(['percentage', 'fixed']),
  discount_val: z.coerce.number().gt(0, 'Must be positive'),
  min_order_amt: z.coerce.number().min(0, 'Cannot be negative'),
  usage_limit: z.coerce.number().gt(0, 'Must be positive'),
  valid_until: z.string().min(1, 'Required'),
})

export default function CouponsPage() {
  const { fetchCoupons, createCoupon, deleteCoupon } = useCoupons()
  const [coupons, setCoupons] = useState<any[]>([])
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

  useEffect(() => {
    loadCoupons()
  }, [])

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
    } catch (error: any) {
      alert(error.message || 'Failed to create coupon')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this coupon?')) return
    try {
      await deleteCoupon(id)
      await loadCoupons()
    } catch (error: any) {
      alert(error.message || 'Failed to delete coupon')
    }
  }

  return (
    <div className="max-w-5xl">
      <h1 className="text-3xl font-bold mb-8 text-gray-900">Coupons</h1>

      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 mb-8">
        <h2 className="text-xl font-bold mb-4">Create New Coupon</h2>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <FormField
                control={form.control}
                name="code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Code</FormLabel>
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
                    <FormLabel>Discount Type</FormLabel>
                    <FormControl>
                      <select
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                        {...field}
                      >
                        <option value="percentage">Percentage (%)</option>
                        <option value="fixed">Fixed Amount ($)</option>
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
                    <FormLabel>Discount Value</FormLabel>
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
                    <FormLabel>Minimum Order ($)</FormLabel>
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
                    <FormLabel>Usage Limit</FormLabel>
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
                    <FormLabel>Valid Until</FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <Button type="submit" disabled={loading}>
              {loading ? 'Creating...' : 'Create Coupon'}
            </Button>
          </form>
        </Form>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Code</TableHead>
              <TableHead>Discount</TableHead>
              <TableHead>Used</TableHead>
              <TableHead>Valid Until</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {coupons.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-gray-500 py-8">
                  No coupons yet.
                </TableCell>
              </TableRow>
            )}
            {coupons.map((coupon) => (
              <TableRow key={coupon.id}>
                <TableCell className="font-mono font-medium">{coupon.code}</TableCell>
                <TableCell>
                  {coupon.discount_type === 'percentage' ? `${coupon.discount_val}%` : `$${coupon.discount_val}`}
                </TableCell>
                <TableCell>{coupon.used_count}</TableCell>
                <TableCell>{new Date(coupon.valid_until).toLocaleDateString()}</TableCell>
                <TableCell className="text-right">
                  <Button variant="destructive" size="sm" onClick={() => handleDelete(coupon.id)}>
                    Delete
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
