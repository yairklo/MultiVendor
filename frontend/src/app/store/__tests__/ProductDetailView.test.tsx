import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ProductDetailView } from '../[tenant_slug]/products/[slug]/ProductDetailView'
import { CartProvider } from '@/context/CartContext'
import { ToastProvider } from '@/context/ToastContext'
import { http, HttpResponse } from 'msw'
import { server } from '../../../mocks/server'
import type { ProductReview } from '@/lib/types'

vi.mock('@/hooks/useCurrency', () => ({
  useCurrency: () => ({
    formatCurrency: (amount: number) => `$${amount}`,
    currency: 'USD',
  }),
}))

const mockProduct = {
  id: 10,
  tenant_id: 1,
  slug: 'artisan-mug',
  name: { en: 'Artisan Ceramic Mug', he: 'ספל קרמיקה איכותי' },
  description: { en: 'Handcrafted ceramic mug for coffee.', he: 'ספל קרמיקה מיוצר בעבודת יד.' },
  base_price: 35,
  primary_image_url: 'https://picsum.photos/seed/mug-1/600/600',
  images: ['https://picsum.photos/seed/mug-1/600/600', 'https://picsum.photos/seed/mug-2/600/600'],
  variants: [{ id: 101, sku: 'MUG-1', stock_quantity: 15 }],
  product_type: 'physical',
  is_active: true,
  show_in_marketplace: true,
  is_bundle: false,
  review_count: 1,
  average_rating: 5,
  created_at: '2026-01-01T00:00:00Z',
}

const mockReviews: ProductReview[] = [
  {
    id: 1,
    product_id: 10,
    user_id: 1,
    customer_name: 'David Cohen',
    rating: 5,
    comment: 'Great mug!',
    is_approved: true,
    is_verified_buyer: true,
    created_at: '2026-02-01T10:00:00Z',
  },
]

describe('ProductDetailView', () => {
  let postedItems: unknown[]

  beforeEach(() => {
    localStorage.clear()
    postedItems = []
    server.use(
      http.post('http://localhost:8000/api/v1/store/:tenant_slug/cart/:cart_id/items', async ({ request }) => {
        postedItems.push(await request.json())
        return HttpResponse.json({ id: 1 }, { status: 201 })
      }),
      http.get('http://localhost:8000/api/v1/store/:tenant_slug/cart/:cart_id', () => {
        return HttpResponse.json({ cart_id: 'mock-cart', tenant_id: 1, items: [], subtotal: 0 })
      })
    )
  })

  const renderView = (productOverrides = {}, reviews = mockReviews) =>
    render(
      <ToastProvider>
        <CartProvider>
          <ProductDetailView
            tenantSlug="test-store"
            slug="artisan-mug"
            product={{ ...mockProduct, ...productOverrides } as any}
            initialReviews={reviews}
          />
        </CartProvider>
      </ToastProvider>
    )

  it('renders product name, price, description, and gallery thumbnails', () => {
    renderView()
    expect(screen.getByText('Artisan Ceramic Mug')).toBeInTheDocument()
    expect(screen.getByText('$35')).toBeInTheDocument()
    expect(screen.getByText('Handcrafted ceramic mug for coffee.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add to Cart' })).toBeInTheDocument()
    expect(screen.getByText('Great mug!')).toBeInTheDocument()
    expect(screen.getByText('David Cohen')).toBeInTheDocument()
  })

  it('allows quantity change and adding to cart', async () => {
    const user = userEvent.setup()
    renderView()

    const plusBtn = screen.getByRole('button', { name: 'Increase quantity' })
    await user.click(plusBtn)

    const addBtn = screen.getByRole('button', { name: 'Add to Cart' })
    await user.click(addBtn)

    await waitFor(() => expect(postedItems).toEqual([{ variant_id: 101, quantity: 2 }]))
  })
})
