import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach } from 'vitest'
import StorefrontPage from '../[tenant_slug]/page'
import { CartProvider } from '@/context/CartContext'
import { http, HttpResponse } from 'msw'
import { server } from '../../../mocks/server'

describe('StorefrontPage', () => {
  let mockCartItems: any[]

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

  const renderStorefront = () =>
    render(
      <CartProvider>
        <StorefrontPage params={{ tenant_slug: 'test-tenant' }} />
      </CartProvider>
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
})
