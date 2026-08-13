import Link from 'next/link'
import { buttonVariants } from '@/components/ui/button'
import { ApiError } from '@/lib/api/apiClient'
import { adminApiClient, getServerTenantSlug } from '@/lib/api/serverApiClient'
import { EditProductClient } from './EditProductClient'

export default async function EditProductPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id: productId } = await params
  const tenantSlug = await getServerTenantSlug()

  let product: any = null
  let error = ''
  try {
    product = await adminApiClient(`/api/v1/admin/store/${tenantSlug}/products/${productId}`)
  } catch (e) {
    error = e instanceof ApiError ? e.message : 'Failed to load product'
  }

  if (!product) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center mb-6 space-x-4">
          <Link href="/admin/products" className={buttonVariants({ variant: 'ghost' })}>
            &larr; Back
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">Edit Product</h1>
        </div>
        <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">{error}</div>
      </div>
    )
  }

  const categoriesData = await adminApiClient(`/api/v1/admin/store/${tenantSlug}/categories`)
  const categories = Array.isArray(categoriesData) ? categoriesData : (categoriesData.data || [])

  const firstVariant = product.variants?.[0] ?? null

  return (
    <EditProductClient
      productId={productId}
      categories={categories}
      initialSlug={product.slug}
      initialVariant={firstVariant}
      initialValues={{
        name_en: typeof product.name === 'object' ? (product.name?.en || '') : (product.name || ''),
        name_he: typeof product.name === 'object' ? (product.name?.he || '') : '',
        description_en: typeof product.description === 'object' ? (product.description?.en || '') : (product.description || ''),
        description_he: typeof product.description === 'object' ? (product.description?.he || '') : '',
        image_url: product.primary_image_url || product.images?.[0] || '',
        base_price: Number(product.base_price),
        category_id: product.category_id ?? null,
        stock_quantity: firstVariant?.stock_quantity ?? 0,
        is_active: product.is_active,
      }}
    />
  )
}
