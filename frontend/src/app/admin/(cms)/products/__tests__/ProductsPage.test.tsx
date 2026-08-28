import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ProductsPageClient } from '../ProductsPageClient'

const fetchProductsMock = vi.fn()
const deleteProductMock = vi.fn()
const fetchCategoriesMock = vi.fn()
const confirmMock = vi.fn()
const showToastMock = vi.fn()

vi.mock('@/hooks/useProducts', () => ({
  useProducts: () => ({ fetchProducts: fetchProductsMock, deleteProduct: deleteProductMock }),
}))

vi.mock('@/hooks/useCategories', () => ({
  useCategories: () => ({ fetchCategories: fetchCategoriesMock }),
}))

vi.mock('@/hooks/useCurrency', () => ({
  useCurrency: () => ({
    formatCurrency: (amount: number) => `$${amount}`,
    currency: 'USD',
  }),
}))

vi.mock('@/context/ToastContext', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

vi.mock('@/context/ConfirmContext', () => ({
  useConfirm: () => ({ confirm: confirmMock }),
}))

const baseProducts = [
  {
    id: 1,
    tenant_id: 1,
    slug: 'vintage-tshirt',
    name: { en: 'Vintage T-Shirt', he: 'חולצה וינטג' },
    description: { en: 'A shirt', he: 'חולצה' },
    base_price: 25,
    category_id: 10,
    is_active: true,
    show_in_marketplace: true,
    product_type: 'physical',
    is_bundle: false,
    variants: [{ id: 100, sku: 'TSHIRT-1', stock_quantity: 5 }],
    primary_image_url: 'https://example.com/tshirt.jpg',
    images: ['https://example.com/tshirt.jpg'],
    review_count: 0,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 2,
    tenant_id: 1,
    slug: 'plain-mug',
    name: { en: 'Plain Mug', he: 'ספל' },
    description: { en: 'A mug', he: 'ספל' },
    base_price: 10,
    category_id: 20,
    is_active: true,
    show_in_marketplace: true,
    product_type: 'physical',
    is_bundle: false,
    variants: [{ id: 101, sku: 'MUG-1', stock_quantity: 3 }],
    primary_image_url: null,
    images: [],
    review_count: 0,
    created_at: '2026-01-01T00:00:00Z',
  },
]

describe('ProductsPageClient', () => {
  beforeEach(() => {
    fetchProductsMock.mockReset()
    deleteProductMock.mockReset()
    fetchCategoriesMock.mockReset()
    confirmMock.mockReset()
    showToastMock.mockReset()
    fetchCategoriesMock.mockResolvedValue([])
    fetchProductsMock.mockResolvedValue({
      data: baseProducts,
      meta: { page: 1, page_size: 20, total: 2, total_pages: 1 },
    })
  })

  it('renders a thumbnail image when a product has an image, and a placeholder otherwise', async () => {
    render(
      <ProductsPageClient
        initialProducts={baseProducts}
        initialMeta={{ page: 1, page_size: 20, total: 2, total_pages: 1 }}
      />
    )

    const img = await screen.findByRole('img', { name: 'Vintage T-Shirt' })
    expect((img as HTMLImageElement).src).toContain('https://example.com/tshirt.jpg')

    expect(screen.getByText(/no image/i)).toBeInTheDocument()
  })

  it('shows a digital badge instead of out-of-stock for a digital product with zero stock', () => {
    render(
      <ProductsPageClient
        initialProducts={[{
          ...baseProducts[0],
          id: 9,
          name: { en: 'Ebook', he: 'ספר' },
          product_type: 'digital',
          variants: [{ id: 200, sku: 'EBOOK-1', stock_quantity: 0 }],
        }]}
        initialMeta={{ page: 1, page_size: 20, total: 1, total_pages: 1 }}
      />
    )

    expect(screen.getByText('Ebook')).toBeInTheDocument()
    expect(screen.getByText(/digital product/i)).toBeInTheDocument()
    expect(screen.queryByText(/out of stock/i)).not.toBeInTheDocument()
  })
})
