import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import LoginPage from '../page'

const pushMock = vi.fn()
const apiClientMock = vi.fn()
const setCookieMock = vi.fn()
let currentSearch = ''

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

vi.mock('cookies-next', () => ({
  setCookie: (...args: unknown[]) => setCookieMock(...args),
}))

async function submitLogin() {
  const user = userEvent.setup()
  render(<LoginPage />)
  // The email/password labels aren't programmatically associated with their
  // inputs (no htmlFor/id) -- pre-existing, out of scope here -- so query by
  // placeholder instead of label text.
  await user.type(screen.getByPlaceholderText('customer@example.com'), 'buyer@example.com')
  await user.type(screen.getByPlaceholderText('••••••••'), 'securepass123')
  await user.click(screen.getByRole('button', { name: /sign in/i }))
}

describe('LoginPage', () => {
  beforeEach(() => {
    pushMock.mockReset()
    apiClientMock.mockReset()
    setCookieMock.mockReset()
    currentSearch = ''
  })

  it('redirects to the ?redirect target on successful login', async () => {
    currentSearch = '?redirect=/checkout'
    apiClientMock.mockResolvedValueOnce({ access_token: 'tok' })

    await submitLogin()

    expect(setCookieMock).toHaveBeenCalledWith('token', 'tok', expect.objectContaining({ path: '/' }))
    expect(pushMock).toHaveBeenCalledWith('/checkout')
  })

  it('falls back to the storefront when there is no redirect param', async () => {
    apiClientMock.mockResolvedValueOnce({ access_token: 'tok' })

    await submitLogin()

    expect(pushMock).toHaveBeenCalledWith('/store/test-tenant')
  })

  it('never redirects off-site, even if ?redirect points elsewhere', async () => {
    currentSearch = `?redirect=${encodeURIComponent('//evil.example.com')}`
    apiClientMock.mockResolvedValueOnce({ access_token: 'tok' })

    await submitLogin()

    expect(pushMock).toHaveBeenCalledWith('/store/test-tenant')
  })
})
