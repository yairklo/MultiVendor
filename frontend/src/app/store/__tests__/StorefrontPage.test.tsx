import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { CatalogListing } from '@/components/storefront/CatalogListing'
import { CartProvider } from '@/context/CartContext'
import { ToastProvider } from '@/context/ToastContext'
import { http, HttpResponse } from 'msw'
import { server } from '../../../mocks/server'
import type { StorePageSchema } from '@/lib/ai/types'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))

// The home page (app/store/[tenant_slug]/page.tsx) is now an async Server
// Component that fetches the AI home layout server-side and isn't renderable
// with RTL — this exercises CatalogListing, the client component that
// actually owns the catalog/search/AI-page-vs-classic-grid behavior.
describe('CatalogListing', () => {
  let mockCartItems: { id: number; variant_id: number; product_name: string; product_type: string; sku: string; attributes: Record<string, string>; unit_price: number; quantity: number; total_price: number }[]

  beforeEach(() => {
    localStorage.clear()
    mockCartItems = []

    server.use(
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

  const renderCatalog = (aiPage: StorePageSchema | null = null) =>
    render(
      <ToastProvider>
        <CartProvider>
          <CatalogListing tenantSlug="test-tenant" aiPage={aiPage} />
        </CartProvider>
      </ToastProvider>
    )

  it('renders the language switcher', async () => {
    renderCatalog()
    expect(await screen.findByTestId('language-switcher')).toBeInTheDocument()
  })

  it('fetches and displays product grid based on tenant slug', async () => {
    renderCatalog()
    expect(await screen.findByTestId('product-grid')).toBeInTheDocument()
    expect(await screen.findByText('Mock Product 1')).toBeInTheDocument()
  })

  it('adds item to cart when Add to Cart button is clicked', async () => {
    const user = userEvent.setup()
    renderCatalog()

    // Wait for data to load
    await screen.findByText('Mock Product 1')

    const addToCartButtons = await screen.findAllByRole('button', { name: /add to cart/i })
    await user.click(addToCartButtons[0])

    // The header/cart badge lives in the shared storefront layout, which this
    // unit test doesn't mount — assert the real side effect instead: the mocked
    // cart POST endpoint actually recorded the item.
    await waitFor(() => expect(mockCartItems).toHaveLength(1))
  })

  it('toggles dir="rtl" and localized strings when switching to Hebrew', async () => {
    const user = userEvent.setup()
    const { container } = renderCatalog()

    await screen.findByTestId('product-grid')
    expect(container.querySelector('[dir]')).toHaveAttribute('dir', 'ltr')

    await user.selectOptions(screen.getByTestId('language-switcher'), 'he')

    expect(container.querySelector('[dir]')).toHaveAttribute('dir', 'rtl')
    expect(await screen.findAllByRole('button', { name: 'הוסף לעגלה' })).toHaveLength(2)
  })

  describe('with an AI-managed home layout', () => {
    const aiPage: StorePageSchema = {
      page_key: 'home',
      page_type: 'static_page',
      title: 'Home',
      sections: [
        { id: 'sec_1', type: 'hero_banner', settings: { headline: 'AI Curated Homepage', size: 'medium' } },
      ],
    }

    it('replaces the classic product grid with the AI layout while browsing', async () => {
      renderCatalog(aiPage)
      expect(await screen.findByText('AI Curated Homepage')).toBeInTheDocument()
      expect(screen.queryByTestId('product-grid')).not.toBeInTheDocument()
    })

    it('falls back to the classic product grid once the shopper searches', async () => {
      const user = userEvent.setup()
      renderCatalog(aiPage)
      await screen.findByText('AI Curated Homepage')

      await user.type(screen.getByLabelText('Search products'), 'Mock')

      expect(await screen.findByTestId('product-grid')).toBeInTheDocument()
      expect(await screen.findByText('Mock Product 1')).toBeInTheDocument()
      expect(screen.queryByText('AI Curated Homepage')).not.toBeInTheDocument()
    })
  })
})
