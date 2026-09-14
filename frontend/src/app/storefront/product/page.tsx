import type { Metadata } from 'next'
import Link from 'next/link'
import { cookies } from 'next/headers'
import { ApiError, getProduct, getProductReviews } from '@/lib/api/serverApiClient'
import { ProductDetailView } from '@/app/store/[tenant_slug]/products/[slug]/ProductDetailView'
import { StorefrontThemeProvider } from '@/context/StorefrontThemeContext'
import { StorefrontHeader } from '@/components/storefront/StorefrontHeader'
import { StorefrontFooter } from '@/components/storefront/StorefrontFooter'
import { StorefrontBrandBackdrop } from '@/components/storefront/StorefrontBrandBackdrop'
import { isUsableTenantSlug } from '@/lib/tenantSlug'
import type { Product } from '@/lib/types'

// Query-param twin of /store/[tenant_slug]/products/[slug] -- same reasoning
// and same removal plan as ../page.tsx (the plain storefront stopgap): that
// route 404s on this deploy for reasons still being tracked, this one
// reuses the exact same ProductDetailView component, just reached via
// ?tenant=<slug>&product=<slug> instead of two stacked dynamic path
// segments. Remove once /store/[tenant_slug]/products/[slug] is confirmed
// working again.

function displayName(slug: string): string {
  return slug
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function productText(product: Product) {
  const name = typeof product.name === 'object' ? (product.name?.en || product.name?.he) : product.name
  const description = typeof product.description === 'object' ? (product.description?.en || product.description?.he) : product.description
  return { name, description }
}

type SearchParams = { tenant?: string; product?: string }

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<SearchParams>
}): Promise<Metadata> {
  const { tenant, product: productSlug } = await searchParams
  if (!tenant || !productSlug) return { title: 'Product not found' }
  try {
    const product = await getProduct(tenant, productSlug)
    const { name, description } = productText(product)
    const image = product.images?.[0] || product.primary_image_url
    return {
      title: name,
      description: description?.slice(0, 160),
      openGraph: { title: name, description: description?.slice(0, 160), images: image ? [image] : undefined },
    }
  } catch {
    return { title: 'Product not found' }
  }
}

export default async function StorefrontProductQueryPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>
}) {
  const { tenant, product: productSlug } = await searchParams
  const tenantSlug = tenant ?? ''

  if (!isUsableTenantSlug(tenantSlug) || !productSlug) {
    return (
      <div className="flex min-h-screen items-center justify-center p-8 text-center">
        <p>Store not found.</p>
      </div>
    )
  }

  let product: Product | null = null
  let error = ''
  try {
    product = await getProduct(tenantSlug, productSlug)
  } catch (e) {
    error = e instanceof ApiError ? e.message : 'Product not found'
  }

  const storeName = displayName(tenantSlug)
  const cookieStore = await cookies()
  const isLoggedIn = !!cookieStore.get('token')?.value

  return (
    <StorefrontThemeProvider tenantSlug={tenantSlug}>
      <StorefrontBrandBackdrop>
        <div className="flex min-h-screen flex-col">
          <StorefrontHeader tenantSlug={tenantSlug} storeName={storeName} isLoggedIn={isLoggedIn} />
          <main className="flex-1">
            {!product ? (
              <div className="p-6 max-w-3xl mx-auto">
                <Link href={`/storefront?slug=${tenantSlug}`} className="text-blue-600 hover:underline">&larr; Back to store</Link>
                <div className="mt-6 p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">
                  {error || 'Product not found'}
                </div>
              </div>
            ) : (
              <ProductDetailView
                tenantSlug={tenantSlug}
                slug={productSlug}
                product={product}
                initialReviews={await getProductReviews(tenantSlug, productSlug)}
              />
            )}
          </main>
          <StorefrontFooter tenantSlug={tenantSlug} storeName={storeName} />
        </div>
      </StorefrontBrandBackdrop>
    </StorefrontThemeProvider>
  )
}
