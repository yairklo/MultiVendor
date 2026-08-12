'use client'

import React, { useState } from 'react'
import { useProducts } from '@/hooks/useProducts'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import * as z from 'zod'

import { Button, buttonVariants } from '@/components/ui/button'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'

const formSchema = z.object({
  name: z.string().min(2, { message: 'Name must be at least 2 characters.' }),
  description: z.string().optional(),
  base_price: z.coerce.number().gt(0, 'Price must be positive'),
  category_id: z.coerce.number().optional().nullable(),
  stock_quantity: z.coerce.number().min(0, 'Quantity cannot be negative'),
  is_active: z.boolean().default(true)
})

export function EditProductClient({
  productId,
  categories,
  initialSlug,
  initialVariant,
  initialValues,
}: {
  productId: string
  categories: any[]
  initialSlug: string
  initialVariant: any
  initialValues: z.infer<typeof formSchema>
}) {
  const router = useRouter()
  const { updateProduct, updateVariant } = useProducts()
  const [slug] = useState(initialSlug)
  const [variant] = useState<any>(initialVariant)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: initialValues,
  })

  const onSubmit = async (values: z.infer<typeof formSchema>) => {
    setLoading(true)
    setError('')
    try {
      const payload = {
        name: { en: values.name, he: values.name },
        description: values.description ? { en: values.description, he: values.description } : undefined,
        base_price: values.base_price,
        category_id: values.category_id || undefined,
        is_active: values.is_active,
      }

      await updateProduct(productId, payload)

      if (variant) {
        await updateVariant(variant.id, {
          sku: variant.sku,
          attributes_json: variant.attributes_json ?? {},
          price_override: variant.price_override ?? null,
          stock_quantity: values.stock_quantity,
        })
      }

      router.push('/admin/products')
    } catch (err: any) {
      setError(err.message || 'Failed to update product')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center mb-6 space-x-4">
        <Link href="/admin/products" className={buttonVariants({ variant: 'ghost' })}>
          &larr; Back
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Edit Product</h1>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">
          {error}
        </div>
      )}

      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Product Name</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. Vintage T-Shirt" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div>
              <label className="text-sm font-medium mb-2 block text-gray-500">Slug</label>
              <Input value={slug} disabled readOnly />
            </div>

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Input placeholder="Description..." {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="base_price"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Base Price ($)</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.01" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="category_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Category (Optional)</FormLabel>
                    <FormControl>
                      <select
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                        value={field.value ?? ''}
                        onChange={e => field.onChange(e.target.value ? Number(e.target.value) : null)}
                      >
                        <option value="">No category</option>
                        {categories.map(cat => (
                          <option key={cat.id} value={cat.id}>
                            {typeof cat.name === 'object' ? (cat.name?.en || cat.name?.he || 'Unnamed') : cat.name}
                          </option>
                        ))}
                      </select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="stock_quantity"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Stock Quantity</FormLabel>
                  <FormControl>
                    <Input type="number" {...field} disabled={!variant} />
                  </FormControl>
                  {!variant && (
                    <p className="text-sm text-muted-foreground">
                      This product has no variant to track stock against.
                    </p>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="is_active"
              render={({ field }) => (
                <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                  <FormControl>
                    <input
                      type="checkbox"
                      checked={field.value}
                      onChange={field.onChange}
                      className="w-4 h-4 text-blue-600 rounded"
                    />
                  </FormControl>
                  <div className="space-y-1 leading-none">
                    <FormLabel>Active</FormLabel>
                    <p className="text-sm text-muted-foreground">
                      This product will be visible on the public storefront.
                    </p>
                  </div>
                </FormItem>
              )}
            />

            <Button type="submit" disabled={loading} className="w-full">
              {loading ? 'Saving...' : 'Save Product'}
            </Button>
          </form>
        </Form>
      </div>
    </div>
  )
}
