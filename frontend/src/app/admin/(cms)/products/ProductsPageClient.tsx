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
import { totalStock, stockLevel, stockLevelLabel, stockLevelClass } from '@/lib/stock'
import { PaginationControls, PaginationMeta } from '@/components/ui/pagination-controls'
import { TableRowSkeleton } from '@/components/ui/skeleton'
import { ExcelImportDialog } from '@/components/upload/ExcelImportDialog'
import { useUploads } from '@/hooks/useUploads'
import { resolveImageUrl } from '@/lib/media'

export function ProductsPageClient({
  initialProducts,
  initialMeta,
}: {
  initialProducts: any[]
  initialMeta: PaginationMeta | null
}) {
  const tenantSlug = useTenantSlug()
  const { fetchProducts, deleteProduct } = useProducts()
  const { showToast } = useToast()
  const { confirm } = useConfirm()
  const { fetchCategories } = useCategories()
  const { formatCurrency } = useCurrency()
  const { previewProductsImport, commitProductsImport, downloadImportTemplate } = useUploads()
  const [products, setProducts] = useState<any[]>(initialProducts)
  const [categories, setCategories] = useState<any[]>([])
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

  const loadProducts = async (pageToLoad = page, s = search, cid = categoryId) => {
    if (!tenantSlug) return
    setLoading(true)
    const { data, meta } = await fetchProducts(pageToLoad, 20, s, cid)
    setProducts(data)
    setMeta(meta)
    setLoading(false)
  }

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
      title: `Delete ${selectedIds.length} products?`,
      description: 'This cannot be undone.',
      confirmLabel: 'Delete All',
      variant: 'destructive',
    })
    if (!ok) return
    try {
      await Promise.all(selectedIds.map(id => deleteProduct(id)))
      setSelectedIds([])
      await loadProducts()
      showToast('Products deleted', 'success')
    } catch (e: any) {
      showToast(e.message || 'Failed to delete some products', 'error')
    }
  }

  const handleDelete = async (id: number) => {
    const ok = await confirm({
      title: 'Delete this product?',
      description: 'This cannot be undone.',
      confirmLabel: 'Delete',
      variant: 'destructive',
    })
    if (!ok) return
    try {
      await deleteProduct(id)
      await loadProducts()
      showToast('Product deleted', 'success')
    } catch (e: any) {
      showToast(e.message || 'Failed to delete product', 'error')
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="font-heading text-3xl font-bold text-foreground">Products</h1>
        <div className="flex space-x-3">
          {selectedIds.length > 0 && (
            <Button variant="destructive" onClick={handleBulkDelete}>
              Delete Selected ({selectedIds.length})
            </Button>
          )}
          <Button variant="outline" onClick={() => setIsImportOpen(true)}>
            Import from Excel
          </Button>
          <Link href="/admin/products/new" className={buttonVariants()}>
            + Add Product
          </Link>
        </div>
      </div>

      <ExcelImportDialog
        open={isImportOpen}
        onOpenChange={setIsImportOpen}
        title="Import Products / Inventory"
        preview={previewProductsImport}
        commit={commitProductsImport}
        onDownloadTemplate={downloadImportTemplate}
        onImported={() => loadProducts()}
      />

      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <Input
          placeholder="Search products..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="max-w-xs"
        />
        <Select
          value={categoryId}
          onValueChange={(value) => setCategoryId(value)}
        >
          <SelectTrigger className="w-full sm:max-w-xs">
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={null}>All Categories</SelectItem>
            {categories.map(cat => (
              <SelectItem key={cat.id} value={cat.id}>
                {typeof cat.name === 'object' ? (cat.name?.en || cat.name?.he || 'Unnamed') : cat.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="bg-card rounded-xl shadow-sm border border-border overflow-hidden">
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
              <TableHead>Product Name</TableHead>
              <TableHead>Price</TableHead>
              <TableHead>Stock</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              Array.from({ length: 5 }, (_, i) => <TableRowSkeleton key={i} columns={6} />)
            ) : products.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">No products found.</TableCell>
              </TableRow>
            ) : (
              products.map(product => {
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
                        alt={typeof product.name === 'object' ? (product.name?.en || 'Product') : product.name}
                        className="w-10 h-10 object-cover rounded"
                      />
                    ) : (
                      <div className="w-10 h-10 bg-muted rounded flex items-center justify-center text-muted-foreground text-[10px] text-center leading-tight">
                        No image
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="font-bold">
                      {typeof product.name === 'object' ? (product.name?.he || product.name?.en || 'Unnamed') : product.name}
                    </div>
                    <div className="text-sm text-muted-foreground truncate max-w-xs">
                      {typeof product.description === 'object' ? (product.description?.he || product.description?.en || '') : (product.description || '')}
                    </div>
                  </TableCell>
                  <TableCell>{formatCurrency(product.base_price)}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{stock}</span>
                      <Badge variant="outline" className={stockLevelClass[level]}>
                        {stockLevelLabel[level]}
                      </Badge>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={product.is_active ? 'success' : 'secondary'}>
                      {product.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Link
                      href={`/admin/products/${product.id}/edit`}
                      className={buttonVariants({ variant: 'ghost', size: 'sm', className: 'mr-2' })}
                    >
                      Edit
                    </Link>
                    <Button variant="destructive" size="sm" onClick={() => handleDelete(product.id)}>Delete</Button>
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
