import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { ProductCard } from '../ProductCard'
import { CartProvider } from '@/context/CartContext'
import { server } from '@/mocks/server'
import { vi } from 'vitest'

vi.mock('@/hooks/useCurrency', () => ({
  useCurrency: () => ({
    formatCurrency: (amount: number) => `$${amount}`,
    currency: 'USD',
  }),
}))

const baseProduct = {
  id: 1,
  tenant_id: 1,
  slug: 'classic-tee',
  name: { en: 'Classic Tee' },
  base_price: 42,
  primary_image_url: 'https://picsum.photos/seed/classic-tee/400/400',
  variants: [{ id: 101, sku: 'TEE-CLASSIC', stock_quantity: 5 }],
  product_type: 'physical' as string,
  is_active: true,
  show_in_marketplace: true,
  is_bundle: false,
  images: [],
  review_count: 0,
  created_at: '2026-01-01T00:00:00Z',
}

describe('ProductCard', () => {
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

  const renderCard = (overrides: Partial<typeof baseProduct> = {}, styleVariant?: 'default' | 'framed' | 'minimal') =>
    render(
      <CartProvider>
        <ProductCard product={{ ...baseProduct, ...overrides }} tenantSlug="test-tenant" styleVariant={styleVariant} />
      </CartProvider>
    )

  it('renders the real product image, name, and price', () => {
    renderCard()
    const img = screen.getByRole('img', { name: 'Classic Tee' }) as HTMLImageElement
    expect(img.src).toContain('picsum.photos')
    expect(screen.getByText('Classic Tee')).toBeInTheDocument()
    expect(screen.getByText('$42')).toBeInTheDocument()
  })

  it('adds the item to the cart when Add to Cart is clicked', async () => {
    const user = userEvent.setup()
    renderCard()

    await user.click(screen.getByRole('button', { name: 'Add to Cart' }))

    await waitFor(() => expect(postedItems).toEqual([{ variant_id: 101, quantity: 1 }]))
  })

  it('disables the button and shows "Out of stock" when every variant is at zero stock', () => {
    renderCard({ variants: [{ id: 101, sku: 'TEE-CLASSIC', stock_quantity: 0 }] })
    const button = screen.getByRole('button', { name: 'Out of stock' })
    expect(button).toBeDisabled()
  })

  it('keeps Add to Cart enabled for a digital product even when stock is zero', () => {
    renderCard({ product_type: 'digital', variants: [{ id: 101, sku: 'TEE-CLASSIC', stock_quantity: 0 }] })
    expect(screen.getByRole('button', { name: 'Add to Cart' })).toBeEnabled()
  })

  it('never emits a card_style class outside the fixed allow-list (AI can restyle, never inject markup)', () => {
    const { container } = renderCard({}, 'framed')
    // framed maps to a specific literal border treatment — proves the settings
    // string actually drives a real, pre-defined class rather than being
    // interpolated into the DOM.
    expect(container.querySelector('.border-2.border-gray-900')).toBeInTheDocument()
  })
})
