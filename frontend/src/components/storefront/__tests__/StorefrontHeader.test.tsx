import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { StorefrontHeader } from '../StorefrontHeader'
import { CartProvider, useCart } from '@/context/CartContext'

vi.mock('next/navigation', () => ({
  usePathname: () => '/store/test-tenant',
}))

function CartOpenProbe() {
  const { isOpen } = useCart()
  return <span data-testid="cart-open-state">{isOpen ? 'open' : 'closed'}</span>
}

describe('StorefrontHeader', () => {
  beforeEach(() => {
    document.cookie = 'token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/'
  })

  const renderHeader = () =>
    render(
      <CartProvider>
        <StorefrontHeader tenantSlug="test-tenant" storeName="Test Tenant" />
        <CartOpenProbe />
      </CartProvider>
    )

  it('renders a link to every core page, always under the tenant slug', () => {
    renderHeader()
    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/store/test-tenant')
    expect(screen.getByRole('link', { name: 'Shop' })).toHaveAttribute('href', '/store/test-tenant/shop')
    expect(screen.getByRole('link', { name: 'About' })).toHaveAttribute('href', '/store/test-tenant/pages/about')
    expect(screen.getByRole('link', { name: 'Contact' })).toHaveAttribute('href', '/store/test-tenant/pages/contact')
  })

  it('opens the cart drawer when the cart button is clicked, and shows the item count', async () => {
    const user = userEvent.setup()
    renderHeader()

    expect(screen.getByTestId('cart-icon')).toHaveTextContent('Cart (0)')
    expect(screen.getByTestId('cart-open-state')).toHaveTextContent('closed')

    await user.click(screen.getByTestId('cart-icon'))

    expect(screen.getByTestId('cart-open-state')).toHaveTextContent('open')
  })

  it('links to Login when signed out, and My Orders when a session token is present', () => {
    const { unmount } = renderHeader()
    expect(screen.getByTestId('account-link')).toHaveTextContent('Login')
    expect(screen.getByTestId('account-link')).toHaveAttribute('href', '/login')
    unmount()

    document.cookie = 'token=fake-jwt; path=/'
    renderHeader()
    expect(screen.getByTestId('account-link')).toHaveTextContent('My Orders')
    expect(screen.getByTestId('account-link')).toHaveAttribute('href', '/account/orders')
  })
})
