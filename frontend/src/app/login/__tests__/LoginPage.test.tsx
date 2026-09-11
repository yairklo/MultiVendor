import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import LoginPage from '../page'

const pushMock = vi.fn()
const apiClientMock = vi.fn()
const setCookieMock = vi.fn()
let currentSearch = ''
let activeCart: { tenantSlug: string; cartId: string } | null = null

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock }),
  useSearchParams: () => new URLSearchParams(currentSearch),
}))

vi.mock('@/lib/api/apiClient', () => ({
  apiClient: (...args: unknown[]) => apiClientMock(...args),
  ApiError: class ApiError extends Error {
    status: number
    constructor(status: number, message: string) {
      super(message)
      this.status = status
    }
  },
}))

vi.mock('@/lib/cart', () => ({
  getActiveCart: () => activeCart,
}))

vi.mock('cookies-next', () => ({
  setCookie: (...args: unknown[]) => setCookieMock(...args),
}))

async function submitLogin() {
  const user = userEvent.setup()
  render(<LoginPage />)
  await user.type(screen.getByLabelText(/email address/i), 'buyer@example.com')
  await user.type(screen.getByLabelText(/^password$/i), 'securepass123')
  await user.click(screen.getByRole('button', { name: /sign in/i }))
}

describe('LoginPage', () => {
  beforeEach(() => {
    pushMock.mockReset()
    apiClientMock.mockReset()
    setCookieMock.mockReset()
    currentSearch = ''
    activeCart = null
  })

  it('redirects to the ?redirect target on successful login', async () => {
    currentSearch = '?redirect=/checkout'
    apiClientMock.mockResolvedValueOnce({ access_token: 'tok' })

    await submitLogin()

    expect(setCookieMock).toHaveBeenCalledWith('token', 'tok', expect.objectContaining({ path: '/' }))
    expect(pushMock).toHaveBeenCalledWith('/checkout')
  })

  it('falls back to the marketplace when there is no redirect param and no active cart', async () => {
    apiClientMock.mockResolvedValueOnce({ access_token: 'tok' })

    await submitLogin()

    expect(apiClientMock).toHaveBeenCalledWith('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: 'buyer@example.com', password: 'securepass123' }),
    })
    expect(pushMock).toHaveBeenCalledWith('/marketplace')
  })

  it('sends the active cart\'s store as tenant_slug and redirects there when no ?redirect is given', async () => {
    activeCart = { tenantSlug: 'coffee-shop', cartId: 'cart-1' }
    apiClientMock.mockResolvedValueOnce({ access_token: 'tok' })

    await submitLogin()

    expect(apiClientMock).toHaveBeenCalledWith('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: 'buyer@example.com', password: 'securepass123', tenant_slug: 'coffee-shop' }),
    })
    expect(pushMock).toHaveBeenCalledWith('/store/coffee-shop')
  })

  it('never redirects off-site, even if ?redirect points elsewhere', async () => {
    currentSearch = `?redirect=${encodeURIComponent('//evil.example.com')}`
    apiClientMock.mockResolvedValueOnce({ access_token: 'tok' })

    await submitLogin()

    expect(pushMock).toHaveBeenCalledWith('/marketplace')
  })
})
