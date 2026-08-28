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
import { ImageUploadField } from '@/components/upload/ImageUploadField'
import { FileUploadField } from '@/components/upload/FileUploadField'
import { resolveImageUrl } from '@/lib/media'
import { useUiLocale } from '@/context/UiLocaleContext'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'
import { extraLanguageCodes, languageDisplayName } from '@/lib/languages'
import { isValidDigitalFileUrl } from '@/lib/digitalFileUrl'
import { errorMessage } from '@/lib/errors'
import type { Category, ProductVariant } from '@/lib/types'

const formSchema = z.object({
  name_en: z.string().min(2, { message: 'English name must be at least 2 characters.' }),
  name_he: z.string().optional(),
  description_en: z.string().optional(),
  description_he: z.string().optional(),
  image_url: z.string().optional(),
  base_price: z.coerce.number().gt(0, 'Price must be positive'),
  category_id: z.coerce.number().optional().nullable(),
  stock_quantity: z.coerce.number().min(0, 'Quantity cannot be negative'),
  is_active: z.boolean(),
  is_digital: z.boolean(),
  digital_file_url: z.string().max(512).refine(isValidDigitalFileUrl, { message: 'Enter an http(s) URL or a path starting with /' }),
})

export function EditProductClient({
  productId,
  categories,
  initialSlug,
  initialVariant,
  initialValues,
  initialExtraNames = {},
  initialExtraDescs = {},
}: {
  productId: string
  categories: Category[]
  initialSlug: string
  initialVariant: ProductVariant | null
  initialValues: z.infer<typeof formSchema>
  initialExtraNames?: Record<string, string>
  initialExtraDescs?: Record<string, string>
}) {
  const router = useRouter()
  const { updateProduct, updateVariant } = useProducts()
  const { t, locale } = useUiLocale()
  const { supportedLanguages } = useStorefrontTheme()
  const extraLangs = extraLanguageCodes(supportedLanguages)
  const [extraNames, setExtraNames] = useState<Record<string, string>>(initialExtraNames)
  const [extraDescs, setExtraDescs] = useState<Record<string, string>>(initialExtraDescs)
  const [slug] = useState(initialSlug)
  const [variant] = useState<ProductVariant | null>(initialVariant)
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
      const descriptionEn = values.description_en?.trim()
      const descriptionHe = values.description_he?.trim()
      const name: Record<string, string> = { en: values.name_en, he: values.name_he || values.name_en }
      for (const lang of extraLangs) {
        name[lang] = extraNames[lang]?.trim() || values.name_he || values.name_en
      }
      const payload: Record<string, unknown> = {
        name,
        base_price: values.base_price,
        category_id: values.category_id || undefined,
        is_active: values.is_active,
        product_type: values.is_digital ? 'digital' : 'physical',
        digital_file_url: values.is_digital ? (values.digital_file_url?.trim() || null) : null,
      }

      if (descriptionEn || descriptionHe || extraLangs.some((l) => extraDescs[l]?.trim())) {
        const description: Record<string, string> = { en: descriptionEn || '', he: descriptionHe || descriptionEn || '' }
        for (const lang of extraLangs) {
          description[lang] = extraDescs[lang]?.trim() || descriptionHe || descriptionEn || ''
        }
        payload.description = description
      }

      // NOTE: server/app/schemas/catalog_schemas.py's ProductUpdateRequest doesn't declare an
      // `images` field yet (only ProductCreateRequest does), so the backend currently ignores
      // this on update. We still send it so the edit flow starts working the moment the backend
      // adds support, without needing another frontend change.
      if (values.image_url) {
        payload.images = [values.image_url]
      }

      await updateProduct(Number(productId), payload)

      if (variant?.id) {
        await updateVariant(variant.id, {
          sku: variant.sku,
          attributes_json: variant.attributes_json ?? {},
          price_override: variant.price_override ?? null,
          stock_quantity: values.is_digital ? 0 : values.stock_quantity,
        })
      }

      router.push('/admin/products')
    } catch (err) {
        setError(errorMessage(err) || t('products.updateFailed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center mb-6 space-x-4">
        <Link href="/admin/products" className={buttonVariants({ variant: 'ghost' })}>
          &larr; {t('common.back')}
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">{t('products.edit')}</h1>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">
          {error}
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
                    <FormLabel>{t('products.nameIn', { language: languageDisplayName('en', locale) })}</FormLabel>
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
                    <FormLabel>{t('products.nameIn', { language: languageDisplayName('he', locale) })}</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. חולצת וינטג'" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            {extraLangs.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {extraLangs.map((lang) => (
                  <div key={`name-${lang}`}>
                    <label className="text-sm font-medium">{t('products.nameIn', { language: languageDisplayName(lang, locale) })}</label>
                    <Input
                      className="mt-2"
                      value={extraNames[lang] || ''}
                      onChange={(e) => setExtraNames((prev) => ({ ...prev, [lang]: e.target.value }))}
                    />
                  </div>
                ))}
              </div>
            )}

            <div>
              <label className="text-sm font-medium mb-2 block text-gray-500">{t('products.slug')}</label>
              <Input value={slug} disabled readOnly />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="description_en"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('products.descriptionIn', { language: languageDisplayName('en', locale) })}</FormLabel>
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
                    <FormLabel>{t('products.descriptionIn', { language: languageDisplayName('he', locale) })}</FormLabel>
                    <FormControl>
                      <Input placeholder="תיאור..." {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            {extraLangs.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {extraLangs.map((lang) => (
                  <div key={`desc-${lang}`}>
                    <label className="text-sm font-medium">{t('products.descriptionIn', { language: languageDisplayName(lang, locale) })}</label>
                    <Input
                      className="mt-2"
                      value={extraDescs[lang] || ''}
                      onChange={(e) => setExtraDescs((prev) => ({ ...prev, [lang]: e.target.value }))}
                    />
                  </div>
                ))}
              </div>
            )}

            <FormField
              control={form.control}
              name="image_url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('products.imageUrl')}</FormLabel>
                  <FormControl>
                    <Input placeholder="https://example.com/image.jpg" {...field} />
                  </FormControl>
                  {field.value && (
                    // eslint-disable-next-line @next/next/no-img-element -- arbitrary vendor URL, no host allowlist
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
              value={form.watch('image_url') || ''}
              onChange={(url) => form.setValue('image_url', url, { shouldDirty: true })}
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="base_price"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('products.basePrice')}</FormLabel>
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
                    <FormLabel>{t('products.category')}</FormLabel>
                    <FormControl>
                      <select
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                        value={field.value ?? ''}
                        onChange={e => field.onChange(e.target.value ? Number(e.target.value) : null)}
                      >
                        <option value="">{t('products.noCategory')}</option>
                        {categories.map(cat => (
                          <option key={cat.id} value={cat.id}>
                            {typeof cat.name === 'object' ? (cat.name?.[locale] || cat.name?.he || cat.name?.en || t('products.unnamed')) : cat.name}
                          </option>
                        ))}
                      </select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {!form.watch('is_digital') && (
            <FormField
              control={form.control}
              name="stock_quantity"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('products.stock')}</FormLabel>
                  <FormControl>
                    <Input type="number" {...field} disabled={!variant} />
                  </FormControl>
                  {!variant && (
                    <p className="text-sm text-muted-foreground">
                      {t('products.noVariantStock')}
                    </p>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />
            )}

            <FormField
              control={form.control}
              name="is_digital"
              render={({ field }) => (
                <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                  <FormControl>
                    <input
                      id="is_digital"
                      type="checkbox"
                      checked={field.value}
                      onChange={field.onChange}
                      className="w-4 h-4 text-blue-600 rounded"
                    />
                  </FormControl>
                  <div className="space-y-1 leading-none">
                    <FormLabel htmlFor="is_digital">{t('products.digitalProduct')}</FormLabel>
                    <p className="text-sm text-muted-foreground">
                      {t('products.digitalHint')}
                    </p>
                  </div>
                </FormItem>
              )}
            />

            {form.watch('is_digital') && (
              <FormField
                control={form.control}
                name="digital_file_url"
                render={({ field }) => (
                  <FormItem>
                    <FileUploadField
                      value={field.value || ''}
                      onChange={field.onChange}
                      label={t('products.uploadFile')}
                      hint={t('products.uploadFileHint')}
                    />
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

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
                    <FormLabel>{t('products.active')}</FormLabel>
                    <p className="text-sm text-muted-foreground">
                      {t('products.activeHint')}
                    </p>
                  </div>
                </FormItem>
              )}
            />

            <Button type="submit" disabled={loading} className="w-full">
              {loading ? t('products.saving') : t('products.saveProduct')}
            </Button>
          </form>
        </Form>
      </div>
    </div>
  )
}
