'use client'

import React, { useEffect, useRef, useState } from 'react'
import { useProducts } from '@/hooks/useProducts'
import { useTenantSlug } from '@/hooks/useTenantSlug'
import Link from 'next/link'
import { useToast } from '@/context/ToastContext'
import { useConfirm } from '@/context/ConfirmContext'
import { useCategories } from '@/hooks/useCategories'
import { useCurrency } from '@/hooks/useCurrency'
import { Input } from '@/components/ui/input'

import { Button, buttonVariants } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { totalStock, stockLevel, stockLevelClass, isDigitalProduct } from '@/lib/stock'
import { PaginationControls, PaginationMeta } from '@/components/ui/pagination-controls'
import { TableRowSkeleton } from '@/components/ui/skeleton'
import { ExcelImportDialog } from '@/components/upload/ExcelImportDialog'
import { useUploads } from '@/hooks/useUploads'
import { resolveImageUrl } from '@/lib/media'
import { useUiLocale } from '@/context/UiLocaleContext'
import { resolveI18nText } from '@/lib/i18n-text'
import { errorMessage } from '@/lib/errors'
import type { Product, Category } from '@/lib/types'

export function ProductsPageClient({
  initialProducts,
  initialMeta,
}: {
  initialProducts: Product[]
  initialMeta: PaginationMeta | null
}) {
  const tenantSlug = useTenantSlug()
  const { fetchProducts, deleteProduct } = useProducts()
  const { showToast } = useToast()
  const { confirm } = useConfirm()
  const { fetchCategories } = useCategories()
  const { formatCurrency } = useCurrency()
  const { t, locale } = useUiLocale()
  const { previewProductsImport, commitProductsImport, downloadImportTemplate } = useUploads()
  const [products, setProducts] = useState<Product[]>(initialProducts)
  const [categories, setCategories] = useState<Category[]>([])
  const [meta, setMeta] = useState<PaginationMeta | null>(initialMeta)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [isImportOpen, setIsImportOpen] = useState(false)

  // Search and Filter
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [categoryId, setCategoryId] = useState<number | null>(null)

  // Bulk Actions
  const [selectedIds, setSelectedIds] = useState<number[]>([])

  const loadProducts = async (pageToLoad = page, s = search, cid = categoryId) => {
    if (!tenantSlug) return
    setLoading(true)
    const { data, meta } = await fetchProducts(pageToLoad, 20, s, cid)
    setProducts(data)
    setMeta(meta)
    setLoading(false)
  }

  useEffect(() => {
    fetchCategories().then(setCategories)
  }, [fetchCategories])

  useEffect(() => {
    const handle = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(handle)
  }, [search])

  const skipInitialFetch = useRef(true)
  useEffect(() => {
    if (skipInitialFetch.current) {
      skipInitialFetch.current = false
      return
    }
    loadProducts(page, debouncedSearch, categoryId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, debouncedSearch, categoryId])

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedIds(products.map(p => p.id))
    } else {
      setSelectedIds([])
    }
  }

  const handleSelectOne = (id: number, checked: boolean) => {
    if (checked) {
      setSelectedIds(prev => [...prev, id])
    } else {
      setSelectedIds(prev => prev.filter(x => x !== id))
    }
  }

  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) return
    const ok = await confirm({
      title: t('products.bulkDeleteConfirm', { count: selectedIds.length }),
      description: t('common.cannotUndo'),
      confirmLabel: t('products.deleteAll'),
      variant: 'destructive',
    })
    if (!ok) return
    try {
      await Promise.all(selectedIds.map(id => deleteProduct(id)))
      setSelectedIds([])
      await loadProducts()
      showToast(t('products.deletedPlural'), 'success')
    } catch (e) {
      showToast(errorMessage(e) || t('products.deleteSomeFailed'), 'error')
    }
  }

  const handleDelete = async (id: number) => {
    const ok = await confirm({
      title: t('products.deleteConfirm'),
      description: t('common.cannotUndo'),
      confirmLabel: t('common.delete'),
      variant: 'destructive',
    })
    if (!ok) return
    try {
      await deleteProduct(id)
      await loadProducts()
      showToast(t('products.deleted'), 'success')
    } catch (e) {
      showToast(errorMessage(e) || t('products.deleteFailed'), 'error')
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="font-heading text-3xl font-bold text-foreground">{t('products.title')}</h1>
        <div className="flex space-x-3">
          {selectedIds.length > 0 && (
            <Button variant="destructive" onClick={handleBulkDelete}>
              {t('products.deleteSelected', { count: selectedIds.length })}
            </Button>
          )}
          <Button variant="outline" onClick={() => setIsImportOpen(true)}>
            {t('products.importExcel')}
          </Button>
          <Link href="/admin/products/new" className={buttonVariants()}>
            {t('products.add')}
          </Link>
        </div>
      </div>

      <ExcelImportDialog
        open={isImportOpen}
        onOpenChange={setIsImportOpen}
        title={t('products.importTitle')}
        preview={previewProductsImport}
        commit={commitProductsImport}
        onDownloadTemplate={downloadImportTemplate}
        onImported={() => loadProducts()}
      />

      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <Input
          placeholder={t('products.searchPlaceholder')}
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="max-w-xs"
        />
        <Select
          value={categoryId}
          onValueChange={(value) => setCategoryId(value)}
        >
          <SelectTrigger className="w-full sm:max-w-xs">
            <SelectValue placeholder={t('products.allCategories')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={null}>{t('products.allCategories')}</SelectItem>
            {categories.map(cat => (
              <SelectItem key={cat.id} value={cat.id}>
                {typeof cat.name === 'object' ? (cat.name?.[locale] || cat.name?.en || cat.name?.he || t('products.unnamed')) : cat.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="min-w-0 overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                <input
                  type="checkbox"
                  checked={products.length > 0 && selectedIds.length === products.length}
                  onChange={handleSelectAll}
                  className="rounded border-input"
                />
              </TableHead>
              <TableHead className="w-16"></TableHead>
              <TableHead>{t('products.name')}</TableHead>
              <TableHead className="text-end">{t('products.basePrice')}</TableHead>
              <TableHead>{t('products.stock')}</TableHead>
              <TableHead>{t('common.status')}</TableHead>
              <TableHead className="text-end">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              Array.from({ length: 5 }, (_, i) => <TableRowSkeleton key={i} columns={7} />)
            ) : products.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-12 text-center text-muted-foreground">{t('products.noProducts')}</TableCell>
              </TableRow>
            ) : (
              products.map(product => {
                const digital = isDigitalProduct(product)
                const stock = totalStock(product.variants)
                const level = stockLevel(stock)
                return (
                <TableRow key={product.id} className="hover:bg-muted/50 transition-colors">
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(product.id)}
                      onChange={(e) => handleSelectOne(product.id, e.target.checked)}
                      className="rounded border-input"
                    />
                  </TableCell>
                  <TableCell>
                    {(product.primary_image_url || (product.images && product.images[0])) ? (
                      // eslint-disable-next-line @next/next/no-img-element -- arbitrary vendor URL, no host allowlist
                      <img
                        src={resolveImageUrl(product.primary_image_url || product.images[0])}
                        alt={resolveI18nText(product.name, locale) || t('products.unnamed')}
                        className="w-10 h-10 object-cover rounded"
                      />
                    ) : (
                      <div className="w-10 h-10 bg-muted rounded flex items-center justify-center text-muted-foreground text-[10px] text-center leading-tight">
                        {t('common.noImage')}
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="font-bold">
                      {resolveI18nText(product.name, locale) || t('products.unnamed')}
                    </div>
                    <div className="text-sm text-muted-foreground truncate max-w-xs">
                      {resolveI18nText(product.description, locale)}
                    </div>
                  </TableCell>
                  <TableCell className="text-end tabular-nums">{formatCurrency(product.base_price)}</TableCell>
                  <TableCell>
                    {digital ? (
                      <Badge variant="secondary">{t('products.digitalProduct')}</Badge>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{stock}</span>
                        <Badge variant="outline" className={stockLevelClass[level]}>
                          {t(`stock.${level}`)}
                        </Badge>
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={product.is_active ? 'success' : 'secondary'}>
                      {product.is_active ? t('products.active') : t('products.inactive')}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-end whitespace-nowrap">
                    <Link
                      href={`/admin/products/${product.id}/edit`}
                      className={buttonVariants({ variant: 'ghost', size: 'sm', className: 'me-2' })}
                    >
                      {t('common.edit')}
                    </Link>
                    <Button variant="destructive" size="sm" onClick={() => handleDelete(product.id)}>{t('common.delete')}</Button>
                  </TableCell>
                </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
        <PaginationControls meta={meta} onPageChange={setPage} />
      </div>
    </div>
  )
}
