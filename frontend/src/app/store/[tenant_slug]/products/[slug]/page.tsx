import { Metadata } from 'next'
import ProductDetailClient from './ProductDetailClient'
import { apiClient } from '@/lib/api/apiClient'

type Params = { tenant_slug: string; slug: string }

export async function generateMetadata(props: { params: Promise<Params> | Params }): Promise<Metadata> {
  const params = await props.params
  
  try {
    // Try to fetch the product to get the real name for SEO
    const product = await apiClient(`/api/v1/store/${params.tenant_slug}/products/${params.slug}`)
    const productName = typeof product.name === 'object' ? (product.name.en || product.name.he) : product.name
    return {
      title: productName || params.slug,
      description: product.description ? String(product.description).substring(0, 160) : `Buy ${productName || params.slug} at ${params.tenant_slug}`,
    }
  } catch (e) {
    // Fallback to slug if API fails
    const decodedSlug = decodeURIComponent(params.slug)
    const title = decodedSlug.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    return {
      title: title,
      description: `Buy ${title} at ${params.tenant_slug}`
    }
  }
}

export default function ProductDetailPage(props: { params: Promise<Params> | Params }) {
  return <ProductDetailClient params={props.params} />
}
