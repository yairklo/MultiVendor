'use client'

import React, { useState, useEffect } from 'react'
import { useProducts } from '@/hooks/useProducts'
import Link from 'next/link'
import { useToast } from '@/context/ToastContext'
import { useConfirm } from '@/context/ConfirmContext'

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
  const [products, setProducts] = useState<any[]>([])
  const [meta, setMeta] = useState<PaginationMeta | null>(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadProducts(page)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page])

  const loadProducts = async (pageToLoad = page) => {
    setLoading(true)
    const { data, meta } = await fetchProducts(pageToLoad)
    setProducts(data)
    setMeta(meta)
    setLoading(false)
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
        <Link href="/admin/products/new" className={buttonVariants()}>
          + Add Product
        </Link>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Product Name</TableHead>
              <TableHead>Price</TableHead>
              <TableHead>Stock</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              Array.from({ length: 5 }, (_, i) => <TableRowSkeleton key={i} columns={5} />)
            ) : products.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-gray-500">No products found.</TableCell>
              </TableRow>
            ) : (
              products.map(product => {
                const stock = totalStock(product.variants)
                const level = stockLevel(stock)
                return (
                <TableRow key={product.id}>
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
