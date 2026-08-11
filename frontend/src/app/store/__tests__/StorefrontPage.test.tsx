import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import StorefrontPage from '../[tenant_slug]/page'
import { CartProvider } from '@/context/CartContext'
import { ToastProvider } from '@/context/ToastContext'
import { http, HttpResponse } from 'msw'
import { server } from '../../../mocks/server'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))

describe('StorefrontPage', () => {
  let mockCartItems: any[]

  beforeEach(() => {
    localStorage.clear()
    mockCartItems = []

    server.use(
      // No AI-managed home layout for this tenant in these tests — the classic
      // product listing below must always be what renders. Mocked explicitly
      // (rather than left unhandled) so this doesn't depend on whatever a real
      // backend happens to have stored for "test-tenant" in a dev environment.
      http.get('http://localhost:8000/api/v1/store/:tenant_slug/pages/:page_key', () => {
        return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
      }),
      http.get('http://localhost:8000/api/v1/store/:tenant_slug/products', () => {
        return HttpResponse.json({
          meta: { total: 2, page: 1, page_size: 10, total_pages: 1 },
          data: [
            { id: 1, name: 'Mock Product 1', price: 99, variants: [{ id: 101 }] },
            { id: 2, name: 'Mock Product 2', price: 149, variants: [{ id: 102 }] }
          ]
        })
      }),
      http.post('http://localhost:8000/api/v1/store/:tenant_slug/cart/:cart_id/items', () => {
        mockCartItems.push({
          id: mockCartItems.length + 1,
          variant_id: 101,
          product_name: 'Mock Product 1',
          product_type: 'physical',
          sku: 'SKU-1',
          attributes: {},
          unit_price: 99,
          quantity: 1,
          total_price: 99,
        })
        return HttpResponse.json({ id: 1 }, { status: 201 })
      }),
      http.get('http://localhost:8000/api/v1/store/:tenant_slug/cart/:cart_id', () => {
        return HttpResponse.json({
          cart_id: 'mock-cart',
          tenant_id: 1,
          items: mockCartItems,
          subtotal: mockCartItems.reduce((sum, i) => sum + i.total_price, 0),
        })
      })
    )
  })

  const renderStorefront = () =>
    render(
      <ToastProvider>
        <CartProvider>
          <StorefrontPage params={{ tenant_slug: 'test-tenant' }} />
        </CartProvider>
      </ToastProvider>
    )

  it('renders tenant logo and language switcher', async () => {
    renderStorefront()
    expect(await screen.findByTestId('tenant-logo')).toBeInTheDocument()
    expect(screen.getByTestId('language-switcher')).toBeInTheDocument()
  })

  it('fetches and displays product grid based on tenant slug', async () => {
    renderStorefront()
    expect(await screen.findByTestId('product-grid')).toBeInTheDocument()
    expect(await screen.findByText('Mock Product 1')).toBeInTheDocument()
  })

  it('adds item to cart when Add to Cart button is clicked', async () => {
    const user = userEvent.setup()
    renderStorefront()

    // Wait for data to load
    await screen.findByText('Mock Product 1')

    const addToCartButtons = await screen.findAllByRole('button', { name: /add to cart/i })
    await user.click(addToCartButtons[0])

    expect(await screen.findByText(/cart \(1\)/i)).toBeInTheDocument()
  })

  it('toggles dir="rtl" and localized strings when switching to Hebrew', async () => {
    const user = userEvent.setup()
    const { container } = renderStorefront()

    await screen.findByTestId('product-grid')
    expect(container.querySelector('[dir]')).toHaveAttribute('dir', 'ltr')

    await user.click(screen.getByTestId('language-switcher'))

    expect(container.querySelector('[dir]')).toHaveAttribute('dir', 'rtl')
    expect(await screen.findByText('עגלה (0)')).toBeInTheDocument()
  })

  describe('with an AI-managed home layout', () => {
    beforeEach(() => {
      server.use(
        http.get('http://localhost:8000/api/v1/store/:tenant_slug/pages/:page_key', () => {
          return HttpResponse.json({
            page_key: 'home',
            page_type: 'static_page',
            title: 'Home',
            sections: [
              { id: 'sec_1', type: 'hero_banner', settings: { headline: 'AI Curated Homepage', size: 'medium' } },
            ],
          })
        })
      )
    })

    it('replaces the classic product grid with the AI layout while browsing', async () => {
      renderStorefront()
      expect(await screen.findByText('AI Curated Homepage')).toBeInTheDocument()
      expect(screen.queryByTestId('product-grid')).not.toBeInTheDocument()
    })

    it('falls back to the classic product grid once the shopper searches', async () => {
      const user = userEvent.setup()
      renderStorefront()
      await screen.findByText('AI Curated Homepage')

      await user.type(screen.getByLabelText('Search products'), 'Mock')

      expect(await screen.findByTestId('product-grid')).toBeInTheDocument()
      expect(await screen.findByText('Mock Product 1')).toBeInTheDocument()
      expect(screen.queryByText('AI Curated Homepage')).not.toBeInTheDocument()
    })
  })
})
