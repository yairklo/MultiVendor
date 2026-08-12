import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ProductsPage from '../page'

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

vi.mock('@/context/ToastContext', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

vi.mock('@/context/ConfirmContext', () => ({
  useConfirm: () => ({ confirm: confirmMock }),
}))

const baseProducts = [
  {
    id: 1,
    name: { en: 'Vintage T-Shirt', he: 'חולצה וינטג' },
    description: { en: 'A shirt', he: 'חולצה' },
    base_price: '25.00',
    category_id: 10,
    is_active: true,
    variants: [{ id: 100, stock_quantity: 5 }],
    primary_image_url: 'https://example.com/tshirt.jpg',
    images: ['https://example.com/tshirt.jpg'],
  },
  {
    id: 2,
    name: { en: 'Plain Mug', he: 'ספל' },
    description: { en: 'A mug', he: 'ספל' },
    base_price: '10.00',
    category_id: 20,
    is_active: true,
    variants: [{ id: 101, stock_quantity: 3 }],
    primary_image_url: null,
    images: [],
  },
]

describe('ProductsPage', () => {
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
    render(<ProductsPage />)

    const img = await screen.findByRole('img', { name: 'Vintage T-Shirt' })
    expect((img as HTMLImageElement).src).toContain('https://example.com/tshirt.jpg')

    expect(screen.getByText(/no image/i)).toBeInTheDocument()
  })
})
