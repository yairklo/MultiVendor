'use client'

import React, { useState, useEffect } from 'react'
import { useProducts } from '@/hooks/useProducts'
import Link from 'next/link'

import { Button, buttonVariants } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

export default function ProductsPage() {
  const { fetchProducts, deleteProduct } = useProducts()
  const [products, setProducts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadProducts()
  }, [])

  const loadProducts = async () => {
    setLoading(true)
    const data = await fetchProducts()
    setProducts(data)
    setLoading(false)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this product?')) return
    try {
      await deleteProduct(id)
      await loadProducts()
    } catch (e: any) {
      alert(e.message || 'Failed to delete product')
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
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center py-8">Loading...</TableCell>
              </TableRow>
            ) : products.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center py-8 text-gray-500">No products found.</TableCell>
              </TableRow>
            ) : (
              products.map(product => (
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
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                      product.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                    }`}>
                      {product.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" className="mr-2">Edit</Button>
                    <Button variant="destructive" size="sm" onClick={() => handleDelete(product.id)}>Delete</Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
