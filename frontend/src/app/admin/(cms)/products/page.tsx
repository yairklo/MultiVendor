'use client'

import React, { useState, useEffect } from 'react'
import { useProducts } from '@/hooks/useProducts'
import Link from 'next/link'
import { useToast } from '@/context/ToastContext'
import { useConfirm } from '@/context/ConfirmContext'
import { useCategories } from '@/hooks/useCategories'
import { Input } from '@/components/ui/input'

import { Button, buttonVariants } from '@/components/ui/button'
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

export default function ProductsPage() {
  const { fetchProducts, deleteProduct } = useProducts()
  const { showToast } = useToast()
  const { confirm } = useConfirm()
  const { fetchCategories } = useCategories()
  const [products, setProducts] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [meta, setMeta] = useState<PaginationMeta | null>(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  
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

  useEffect(() => {
    loadProducts(page, debouncedSearch, categoryId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, debouncedSearch, categoryId])

  const loadProducts = async (pageToLoad = page, s = search, cid = categoryId) => {
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
        <h1 className="text-3xl font-bold text-gray-900">Products</h1>
        <div className="flex space-x-3">
          {selectedIds.length > 0 && (
            <Button variant="destructive" onClick={handleBulkDelete}>
              Delete Selected ({selectedIds.length})
            </Button>
          )}
          <Link href="/admin/products/new" className={buttonVariants()}>
            + Add Product
          </Link>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <Input 
          placeholder="Search products..." 
          value={search} 
          onChange={e => setSearch(e.target.value)} 
          className="max-w-xs"
        />
        <select 
          className="flex h-10 w-full sm:max-w-xs items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          value={categoryId || ''}
          onChange={e => setCategoryId(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">All Categories</option>
          {categories.map(cat => (
            <option key={cat.id} value={cat.id}>
              {typeof cat.name === 'object' ? (cat.name?.en || cat.name?.he || 'Unnamed') : cat.name}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                <input 
                  type="checkbox" 
                  checked={products.length > 0 && selectedIds.length === products.length}
                  onChange={handleSelectAll}
                  className="rounded border-gray-300"
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
                <TableCell colSpan={6} className="text-center py-8 text-gray-500">No products found.</TableCell>
              </TableRow>
            ) : (
              products.map(product => {
                const stock = totalStock(product.variants)
                const level = stockLevel(stock)
                return (
                <TableRow key={product.id}>
                  <TableCell>
                    <input 
                      type="checkbox" 
                      checked={selectedIds.includes(product.id)}
                      onChange={(e) => handleSelectOne(product.id, e.target.checked)}
                      className="rounded border-gray-300"
                    />
                  </TableCell>
                  <TableCell>
                    {(product.primary_image_url || (product.images && product.images[0])) ? (
                      <img 
                        src={product.primary_image_url || product.images[0]} 
                        alt={typeof product.name === 'object' ? (product.name?.en || 'Product') : product.name} 
                        className="w-10 h-10 object-cover rounded"
                      />
                    ) : (
                      <div className="w-10 h-10 bg-gray-100 rounded flex items-center justify-center text-gray-400 text-[10px] text-center leading-tight">
                        No image
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="font-bold">
                      {typeof product.name === 'object' ? (product.name?.he || product.name?.en || 'Unnamed') : product.name}
                    </div>
                    <div className="text-sm text-gray-500 truncate max-w-xs">
                      {typeof product.description === 'object' ? (product.description?.he || product.description?.en || '') : (product.description || '')}
                    </div>
                  </TableCell>
                  <TableCell>${product.base_price}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{stock}</span>
                      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${stockLevelClass[level]}`}>
                        {stockLevelLabel[level]}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                      product.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                    }`}>
                      {product.is_active ? 'Active' : 'Inactive'}
                    </span>
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
