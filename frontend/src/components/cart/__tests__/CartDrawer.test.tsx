import React, { useEffect } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { CartProvider, useCart } from '@/context/CartContext'
import { CartDrawer } from '../CartDrawer'
import type { Cart } from '@/lib/cart'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

let mockCart: Cart

vi.mock('@/lib/cart', async () => {
  const actual = await vi.importActual<typeof import('@/lib/cart')>('@/lib/cart')
  return {
    ...actual,
    getActiveCart: () => ({ tenantSlug: 'test-tenant', cartId: 'cart-1' }),
    fetchCart: () => Promise.resolve(mockCart),
    updateItemQuantity: vi.fn(async (_tenant: string, _cartId: string, itemId: number, quantity: number) => {
      const item = mockCart.items.find(i => i.id === itemId)
      if (item) {
        item.quantity = quantity
        item.total_price = quantity * item.unit_price
      }
      mockCart = { ...mockCart, subtotal: mockCart.items.reduce((s, i) => s + i.total_price, 0) }
    }),
    removeCartItem: vi.fn(async (_tenant: string, _cartId: string, itemId: number) => {
      const items = mockCart.items.filter(i => i.id !== itemId)
      mockCart = { ...mockCart, items, subtotal: items.reduce((s, i) => s + i.total_price, 0) }
    }),
  }
})

function OpenDrawerOnMount() {
  const { openDrawer } = useCart()
  useEffect(() => { openDrawer() }, [openDrawer])
  return null
}

describe('CartDrawer', () => {
  beforeEach(() => {
    mockCart = {
      cart_id: 'cart-1',
      tenant_id: 1,
      subtotal: 50,
      items: [
        {
          id: 1,
          variant_id: 10,
          product_name: 'Widget',
          product_type: 'physical',
          sku: 'SKU-1',
          attributes: {},
          unit_price: 25,
          quantity: 2,
          total_price: 50,
        },
      ],
    }
  })

  const renderDrawer = () =>
    render(
      <CartProvider>
        <OpenDrawerOnMount />
        <CartDrawer />
      </CartProvider>
    )

  it('shows item details and the subtotal', async () => {
    renderDrawer()
    expect(await screen.findByTestId('cart-drawer')).toBeInTheDocument()
    const item = screen.getByTestId('cart-item')
    expect(item).toHaveTextContent('Widget')
    expect(item).toHaveTextContent('2')
    expect(screen.getByTestId('cart-subtotal')).toHaveTextContent('50')
  })

  it('increments and decrements quantity, updating the subtotal live', async () => {
    const user = userEvent.setup()
    renderDrawer()
    await screen.findByTestId('cart-drawer')

    await user.click(screen.getByRole('button', { name: /increase quantity/i }))
    expect(await screen.findByTestId('cart-subtotal')).toHaveTextContent('75')

    await user.click(screen.getByRole('button', { name: /decrease quantity/i }))
    expect(await screen.findByTestId('cart-subtotal')).toHaveTextContent('50')
  })

  it('removes an item from the cart', async () => {
    const user = userEvent.setup()
    renderDrawer()
    await screen.findByTestId('cart-drawer')

    await user.click(screen.getByRole('button', { name: /remove item/i }))
    expect(await screen.findByText(/your cart is empty/i)).toBeInTheDocument()
  })
})
