'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { apiClient } from '@/lib/api/apiClient'
import { useCart } from '@/context/CartContext'
import { totalStock } from '@/lib/stock'

type Params = { tenant_slug: string; slug: string }

export default function ProductDetailPage(props: { params: Promise<Params> | Params }) {
  const isPromise = props.params instanceof Promise
  const [params, setParams] = useState<Params | null>(isPromise ? null : (props.params as Params))

  useEffect(() => {
    if (isPromise) {
      ;(props.params as Promise<Params>).then(setParams)
    }
  }, [props.params, isPromise])

  const [product, setProduct] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [adding, setAdding] = useState(false)
  const { addItem, openDrawer } = useCart()

  useEffect(() => {
    if (!params) return
    setLoading(true)
    apiClient(`/api/v1/store/${params.tenant_slug}/products/${params.slug}`)
      .then(data => {
        setProduct(data)
        setQuantity(1)
      })
      .catch((e: any) => setError(e.message || 'Product not found'))
      .finally(() => setLoading(false))
  }, [params])

  if (!params || loading) {
    return <div className="p-6 text-gray-600">Loading...</div>
  }

  if (error || !product) {
    return (
      <div className="p-6 max-w-3xl mx-auto">
        <Link href={`/store/${params.tenant_slug}`} className="text-blue-600 hover:underline">&larr; Back to store</Link>
        <div className="mt-6 p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">
          {error || 'Product not found'}
        </div>
      </div>
    )
  }

  const stock = totalStock(product.variants)
  const stockKnown = Number.isFinite(stock)
  const outOfStock = stockKnown && stock <= 0
  const name = typeof product.name === 'object' ? (product.name?.en || product.name?.he) : product.name
  const description = typeof product.description === 'object' ? (product.description?.en || product.description?.he) : product.description
  const images: string[] = product.images?.length ? product.images : (product.primary_image_url ? [product.primary_image_url] : [])

  const clampQuantity = (qty: number) => Math.max(1, Math.min(qty, stockKnown ? Math.max(stock, 1) : qty))

  const handleAddToCart = async () => {
    const variantId = product.variants?.[0]?.id
    if (!variantId) return
    setAdding(true)
    try {
      await addItem(params.tenant_slug, variantId, quantity)
      openDrawer()
    } catch (e) {
      console.error('Failed to add item to cart:', e)
    } finally {
      setAdding(false)
    }
  }

  return (
    <div className="p-4 bg-gray-50 min-h-screen text-gray-900">
      <div className="max-w-4xl mx-auto">
        <Link href={`/store/${params.tenant_slug}`} className="text-blue-600 hover:underline">&larr; Back to store</Link>

        <div className="mt-4 bg-white rounded-xl shadow-md border border-gray-100 p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            {images.length > 0 ? (
              <img src={images[0]} alt={name} className="w-full h-80 object-cover rounded-lg" />
            ) : (
              <div className="w-full h-80 bg-gray-100 rounded-lg flex items-center justify-center text-gray-400">
                No image
              </div>
            )}
          </div>

          <div>
            <h1 className="text-2xl font-bold mb-2">{name}</h1>
            <p className="text-xl text-gray-700 mb-4">${product.base_price}</p>
            {description && <p className="text-gray-600 mb-4">{description}</p>}

            {stockKnown && (
              <p className={`text-sm mb-4 ${outOfStock ? 'text-red-600 font-medium' : 'text-gray-400'}`}>
                {outOfStock ? 'Out of stock' : `${stock} in stock`}
              </p>
            )}

            {!outOfStock && (
              <div className="flex items-center gap-2 mb-4">
                <button
                  type="button"
                  aria-label="Decrease quantity"
                  onClick={() => setQuantity(q => clampQuantity(q - 1))}
                  className="w-8 h-8 border rounded-lg text-gray-700 hover:bg-gray-100"
                >
                  &minus;
                </button>
                <input
                  type="number"
                  aria-label="Quantity"
                  min={1}
                  max={stockKnown ? stock : undefined}
                  value={quantity}
                  onChange={e => setQuantity(clampQuantity(Number(e.target.value) || 1))}
                  className="w-14 text-center border rounded-lg py-1"
                />
                <button
                  type="button"
                  aria-label="Increase quantity"
                  onClick={() => setQuantity(q => clampQuantity(q + 1))}
                  className="w-8 h-8 border rounded-lg text-gray-700 hover:bg-gray-100"
                >
                  +
                </button>
              </div>
            )}

            <button
              onClick={handleAddToCart}
              disabled={outOfStock || adding}
              className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {outOfStock ? 'Out of stock' : adding ? 'Adding...' : 'Add to Cart'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
