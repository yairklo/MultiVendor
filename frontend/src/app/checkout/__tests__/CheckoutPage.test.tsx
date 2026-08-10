import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import CheckoutPage from '../page'
import { CartProvider } from '@/context/CartContext'
import { ToastProvider } from '@/context/ToastContext'
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

const renderCheckout = () => render(<ToastProvider><CartProvider><CheckoutPage /></CartProvider></ToastProvider>)

describe('CheckoutPage', () => {
  beforeEach(() => {
    mockedCart = physicalCart
    clearCartMock.mockClear()
    server.use(
      http.post('http://localhost:8000/api/v1/store/test-tenant/cart/checkout', () => {
        return HttpResponse.json({ id: 1, order_number: 'ORD-1', total_amount: 99, status: 'pending_payment' }, { status: 201 })
      }),
      http.post('http://localhost:8000/api/v1/customer/orders/1/pay', () => {
        return HttpResponse.json({ id: 1, order_number: 'ORD-1', total_amount: 99, status: 'processing' }, { status: 200 })
      })
    )
  })

  it('renders item summary, shipping methods, coupon inputs, and shipping address for a physical cart', async () => {
    renderCheckout()
    expect(await screen.findByTestId('item-summary')).toBeInTheDocument()
    expect(screen.getByText(/Premium Product/i)).toBeInTheDocument()
    expect(screen.getByTestId('shipping-methods')).toBeInTheDocument()
    expect(screen.getByTestId('coupon-input')).toBeInTheDocument()
    expect(screen.getByTestId('shipping-address-fields')).toBeInTheDocument()
  })

  it('hides shipping address fields when the cart is digital-only', async () => {
    mockedCart = digitalCart
    renderCheckout()
    expect(await screen.findByTestId('item-summary')).toBeInTheDocument()
    expect(screen.queryByTestId('shipping-address-fields')).not.toBeInTheDocument()
  })

  it('submits checkout, then completes the mock payment step', async () => {
    const user = userEvent.setup()
    renderCheckout()

    await screen.findByTestId('item-summary')
    const submitButton = screen.getByRole('button', { name: /place order/i })
    await user.click(submitButton)

    // Checkout no longer finalizes the order outright — it creates it
    // awaiting a (mock) payment step.
    expect(await screen.findByTestId('pending-payment')).toBeInTheDocument()
    expect(screen.getByText(/awaiting payment/i)).toBeInTheDocument()
    await waitFor(() => expect(clearCartMock).toHaveBeenCalled())

    const payButton = screen.getByRole('button', { name: /pay now/i })
    await user.click(payButton)

    expect(await screen.findByText(/payment successful/i)).toBeInTheDocument()
  })

  it('applies a coupon and reflects the discount in the total', async () => {
    const user = userEvent.setup()
    server.use(
      http.post('http://localhost:8000/api/v1/store/test-tenant/coupons/validate', () => {
        return HttpResponse.json({ id: 1, code: 'SAVE10', discount_type: 'percentage', discount_val: 10, used_count: 0, valid_until: '2037-01-01T00:00:00Z' })
      })
    )
    renderCheckout()

    await screen.findByTestId('item-summary')
    await user.type(screen.getByPlaceholderText(/enter code/i), 'SAVE10')
    await user.click(screen.getByRole('button', { name: /apply/i }))

    expect(await screen.findByText(/SAVE10 applied/i)).toBeInTheDocument()
    expect(screen.getByText('-$9.90')).toBeInTheDocument()
    expect(screen.getByText('$89.10')).toBeInTheDocument()
  })
})
