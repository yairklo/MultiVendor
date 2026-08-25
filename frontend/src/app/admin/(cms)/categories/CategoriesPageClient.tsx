'use client'

import React, { useState } from 'react'
import { useCategories } from '@/hooks/useCategories'
import { useToast } from '@/context/ToastContext'
import { useConfirm } from '@/context/ConfirmContext'
import { useUiLocale } from '@/context/UiLocaleContext'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'
import { resolveI18nText } from '@/lib/i18n-text'
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
  name: z.string().min(2, { message: 'Name must be at least 2 characters.' }),
  slug: z.string().min(2, { message: 'Slug must be at least 2 characters.' }).regex(/^[a-z0-9-]+$/, 'Slug must be lowercase alphanumeric and hyphens only.'),
})

export function CategoriesPageClient({ initialCategories }: { initialCategories: any[] }) {
  const { fetchCategories, createCategory, deleteCategory } = useCategories()
  const { showToast } = useToast()
  const { confirm } = useConfirm()
  const { t, locale } = useUiLocale()
  const { supportedLanguages } = useStorefrontTheme()
  const [categories, setCategories] = useState<any[]>(initialCategories)
  const [loading, setLoading] = useState(false)

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: '',
      slug: '',
    },
  })

  const loadCategories = async () => {
    const data = await fetchCategories()
    setCategories(data)
  }

  async function onSubmit(values: z.infer<typeof formSchema>) {
    setLoading(true)
    try {
      const name: Record<string, string> = {}
      const langs = supportedLanguages.length ? supportedLanguages : ['en', 'he']
      for (const lang of langs) name[lang] = values.name
      if (!name.en) name.en = values.name
      if (!name.he) name.he = values.name
      const payload = { name, slug: values.slug }
      await createCategory(payload)
      form.reset()
      await loadCategories()
      showToast(t('categories.created'), 'success')
    } catch (error: any) {
      showToast(error.message || t('categories.createFailed'), 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    const ok = await confirm({
      title: t('categories.deleteConfirm'),
      confirmLabel: t('common.delete'),
      variant: 'destructive',
    })
    if (!ok) return
    try {
      await deleteCategory(id)
      await loadCategories()
      showToast(t('categories.deleted'), 'success')
    } catch (error: any) {
      showToast(error.message || t('categories.deleteFailed'), 'error')
    }
  }

  return (
    <div className="max-w-5xl">
      <h1 className="font-heading text-3xl font-bold mb-8 text-foreground">{t('categories.title')}</h1>

      <div className="bg-card p-6 rounded-xl shadow-sm border border-border mb-8">
        <h2 className="text-xl font-bold mb-4 text-foreground">{t('categories.addNew')}</h2>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('categories.name')}</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. Electronics" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="slug"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('categories.slug')}</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. electronics" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <Button type="submit" disabled={loading}>
              {loading ? t('common.creating') : t('categories.create')}
            </Button>
          </form>
        </Form>
      </div>

      <div className="min-w-0 overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('categories.categoryName')}</TableHead>
              <TableHead>{t('categories.slug')}</TableHead>
              <TableHead className="text-end">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {categories.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground py-8">
                  {t('categories.none')}
                </TableCell>
              </TableRow>
            )}
            {categories.map((cat) => (
              <TableRow key={cat.id} className="hover:bg-muted/50 transition-colors">
                <TableCell className="font-medium">
                  {resolveI18nText(cat.name, locale) || t('products.unnamed')}
                </TableCell>
                <TableCell>{cat.slug}</TableCell>
                <TableCell className="text-end whitespace-nowrap">
                  <Button variant="destructive" size="sm" onClick={() => handleDelete(cat.id)}>
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
