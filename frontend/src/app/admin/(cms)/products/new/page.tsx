'use client'

import React, { useState, useEffect } from 'react'
import { useProducts } from '@/hooks/useProducts'
import { useCategories } from '@/hooks/useCategories'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ApiError } from '@/lib/api/apiClient'
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
// Temporarily using standard select if shadcn select is complex, or checkbox for active
// Actually, shadcn select is installed. But let's keep it simple for boolean
import { Label } from '@/components/ui/label'
import { ImageUploadField } from '@/components/upload/ImageUploadField'
import { resolveImageUrl } from '@/lib/media'

const formSchema = z.object({
  name_en: z.string().min(2, { message: 'English name must be at least 2 characters.' }),
  name_he: z.string().optional(),
  slug: z.string().min(2).regex(/^[a-z0-9-]+$/, 'Lowercase alphanumeric and hyphens only.'),
  description_en: z.string().optional(),
  description_he: z.string().optional(),
  image_url: z.string().optional(),
  base_price: z.coerce.number().min(0, 'Price must be positive'),
  category_id: z.coerce.number().optional().nullable(),
  stock_quantity: z.coerce.number().min(0, 'Quantity cannot be negative'),
  is_active: z.boolean().default(true)
})

export default function NewProductPage() {
  const router = useRouter()
  const { createProduct } = useProducts()
  const { fetchCategories } = useCategories()
  const [categories, setCategories] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [limitReached, setLimitReached] = useState(false)

  useEffect(() => {
    fetchCategories().then(setCategories)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name_en: '',
      name_he: '',
      slug: '',
      description_en: '',
      description_he: '',
      image_url: '',
      base_price: 0,
      category_id: null,
      stock_quantity: 10,
      is_active: true
    },
  })

  const onSubmit = async (values: z.infer<typeof formSchema>) => {
    setLoading(true)
    setError('')
    setLimitReached(false)
    try {
      // Transform flat form data to match backend ProductCreateRequest schema
      const descriptionEn = values.description_en?.trim()
      const descriptionHe = values.description_he?.trim()
      const payload: any = {
        name: { en: values.name_en, he: values.name_he || values.name_en },
        slug: values.slug,
        base_price: values.base_price,
        category_id: values.category_id || undefined,
        is_active: values.is_active,
        images: values.image_url ? [values.image_url] : [],
        variants: [
          {
            sku: `${values.slug.toUpperCase()}-DEFAULT`,
            stock_quantity: values.stock_quantity,
            attributes_json: {}
          }
        ]
      }

      if (descriptionEn || descriptionHe) {
        payload.description = { en: descriptionEn || '', he: descriptionHe || descriptionEn || '' }
      }
      
      await createProduct(payload)
      router.push('/admin/products')
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 403) {
        setLimitReached(true)
      } else {
        setError(err.message || 'Failed to create product')
      }
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
        <h1 className="text-3xl font-bold text-gray-900">Add New Product</h1>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">
          {error}
        </div>
      )}

      {limitReached && (
        <div data-testid="upgrade-prompt" className="mb-6 p-4 bg-amber-50 text-amber-800 rounded-lg border border-amber-200 flex items-center justify-between gap-4">
          <span>You&apos;ve reached your plan&apos;s product limit. Upgrade your plan to add more products.</span>
          <Link href="/admin/settings" className={buttonVariants({ variant: 'default', size: 'sm' })}>
            Upgrade Plan
          </Link>
        </div>
      )}

      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="name_en"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Product Name (English)</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. Vintage T-Shirt" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="name_he"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Product Name (Hebrew)</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. חולצת וינטג'" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            
            <FormField
              control={form.control}
              name="slug"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Slug</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. vintage-tshirt" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="description_en"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description (English)</FormLabel>
                    <FormControl>
                      <Input placeholder="Description..." {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="description_he"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description (Hebrew)</FormLabel>
                    <FormControl>
                      <Input placeholder="תיאור..." {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="image_url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Image URL</FormLabel>
                  <FormControl>
                    <Input placeholder="https://example.com/image.jpg" {...field} />
                  </FormControl>
                  {field.value && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={resolveImageUrl(field.value)}
                      alt="Preview"
                      className="mt-2 h-24 w-24 rounded-lg border border-gray-100 object-cover"
                    />
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            <ImageUploadField
              label="Upload Image File"
              value={form.watch('image_url') || ''}
              onChange={(url) => form.setValue('image_url', url, { shouldDirty: true })}
            />

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                name="stock_quantity"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Initial Stock Quantity</FormLabel>
                    <FormControl>
                      <Input type="number" {...field} />
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
