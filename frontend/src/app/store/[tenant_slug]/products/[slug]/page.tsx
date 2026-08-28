import type { Metadata } from 'next'
import Link from 'next/link'
import { ApiError, getProduct, getProductReviews } from '@/lib/api/serverApiClient'
import { ProductDetailView } from './ProductDetailView'
import type { Product } from '@/lib/types'

type Params = { tenant_slug: string; slug: string }

function productText(product: Product) {
  const name = typeof product.name === 'object' ? (product.name?.en || product.name?.he) : product.name
  const description = typeof product.description === 'object' ? (product.description?.en || product.description?.he) : product.description
  return { name, description }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>
}): Promise<Metadata> {
  const { tenant_slug, slug } = await params
  try {
    const product = await getProduct(tenant_slug, slug)
    const { name, description } = productText(product)
    const image = product.images?.[0] || product.primary_image_url
    return {
      title: name,
      description: description?.slice(0, 160),
      openGraph: {
        title: name,
        description: description?.slice(0, 160),
        images: image ? [image] : undefined,
      },
    }
  } catch {
    return { title: 'Product not found' }
  }
}

export default async function ProductDetailPage({
  params,
}: {
  params: Promise<Params>
}) {
  const { tenant_slug: tenantSlug, slug } = await params

  let product: Product | null = null
  let error = ''
  try {
    product = await getProduct(tenantSlug, slug)
  } catch (e) {
    error = e instanceof ApiError ? e.message : 'Product not found'
  }

  if (!product) {
    return (
      <div className="p-6 max-w-3xl mx-auto">
        <Link href={`/store/${tenantSlug}`} className="text-blue-600 hover:underline">&larr; Back to store</Link>
        <div className="mt-6 p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">
          {error || 'Product not found'}
        </div>
      </div>
    )
  }

  const reviews = await getProductReviews(tenantSlug, slug)

  return <ProductDetailView tenantSlug={tenantSlug} slug={slug} product={product} initialReviews={reviews} />
}
