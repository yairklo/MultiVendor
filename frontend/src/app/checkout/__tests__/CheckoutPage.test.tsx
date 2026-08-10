import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import CheckoutPage from '../page'
import { CartProvider } from '@/context/CartContext'
import { http, HttpResponse } from 'msw'
import { server } from '../../../mocks/server'
import type { Cart } from '@/lib/cart'

const physicalCart: Cart = {
  cart_id: 'cart-1',
  tenant_id: 1,
  subtotal: 99,
  items: [
    {
      id: 1,
      variant_id: 10,
      product_name: 'Premium Product',
      product_type: 'physical',
      sku: 'SKU-1',
      attributes: {},
      unit_price: 99,
      quantity: 1,
      total_price: 99,
    },
  ],
}

const digitalCart: Cart = {
  ...physicalCart,
  items: [{ ...physicalCart.items[0], product_type: 'digital', product_name: 'Ebook' }],
}

const clearCartMock = vi.fn()
let mockedCart: Cart = physicalCart

vi.mock('@/lib/cart', async () => {
  const actual = await vi.importActual<typeof import('@/lib/cart')>('@/lib/cart')
  return {
    ...actual,
    getActiveCart: () => ({ tenantSlug: 'test-tenant', cartId: 'cart-1' }),
    fetchCart: () => Promise.resolve(mockedCart),
    clearCart: () => clearCartMock(),
  }
})

describe('CheckoutPage', () => {
  beforeEach(() => {
    mockedCart = physicalCart
    clearCartMock.mockClear()
    server.use(
      http.post('http://localhost:8000/api/v1/store/test-tenant/cart/checkout', () => {
        return HttpResponse.json({ id: 1, order_number: 'ORD-1' }, { status: 201 })
      })
    )
  })

  it('renders item summary, shipping methods, coupon inputs, and shipping address for a physical cart', async () => {
    render(<CartProvider><CheckoutPage /></CartProvider>)
    expect(await screen.findByTestId('item-summary')).toBeInTheDocument()
    expect(screen.getByText(/Premium Product/i)).toBeInTheDocument()
    expect(screen.getByTestId('shipping-methods')).toBeInTheDocument()
    expect(screen.getByTestId('coupon-input')).toBeInTheDocument()
    expect(screen.getByTestId('shipping-address-fields')).toBeInTheDocument()
  })

  it('hides shipping address fields when the cart is digital-only', async () => {
    mockedCart = digitalCart
    render(<CartProvider><CheckoutPage /></CartProvider>)
    expect(await screen.findByTestId('item-summary')).toBeInTheDocument()
    expect(screen.queryByTestId('shipping-address-fields')).not.toBeInTheDocument()
  })

  it('submits checkout and shows a success message', async () => {
    const user = userEvent.setup()
    render(<CartProvider><CheckoutPage /></CartProvider>)

    await screen.findByTestId('item-summary')
    const submitButton = screen.getByRole('button', { name: /place order/i })
    await user.click(submitButton)

    const confirmations = await screen.findAllByText(/order placed/i)
    expect(confirmations.length).toBeGreaterThan(0)
    await waitFor(() => expect(clearCartMock).toHaveBeenCalled())
  })
})
