import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import SignupPage from '../page'

const pushMock = vi.fn()
const apiClientMock = vi.fn()
const setCookieMock = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock }),
  useSearchParams: () => new URLSearchParams(),
}))

vi.mock('@/lib/api/apiClient', () => ({
  apiClient: (...args: unknown[]) => apiClientMock(...args),
}))

vi.mock('cookies-next', () => ({
  setCookie: (...args: unknown[]) => setCookieMock(...args),
}))

describe('SignupPage', () => {
  beforeEach(() => {
    pushMock.mockReset()
    apiClientMock.mockReset()
    setCookieMock.mockReset()
    // jsdom doesn't implement navigation; the seller flow triggers it after
    // a successful submit, which we don't need to observe.
    delete (window as unknown as { location?: unknown }).location
    ;(window as unknown as { location: { assign: (url: string) => void } }).location = { assign: vi.fn() }
  })

  it('defaults to the customer form and registers via /auth/register', async () => {
    apiClientMock.mockResolvedValueOnce({ access_token: 'tok', role: 'user', store_role: null })
    const user = userEvent.setup()

    render(<SignupPage />)

    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/store name/i)).not.toBeInTheDocument()

    await user.type(screen.getByLabelText(/full name/i), 'Jane Doe')
    await user.type(screen.getByLabelText(/email address/i), 'jane@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'securepass123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(apiClientMock).toHaveBeenCalledWith('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email: 'jane@example.com', password: 'securepass123', full_name: 'Jane Doe' }),
    })
    expect(setCookieMock).toHaveBeenCalledWith('token', 'tok', expect.objectContaining({ path: '/' }))
    expect(pushMock).toHaveBeenCalledWith('/marketplace')
  })

  it('switches to the seller form and registers via /auth/register-tenant', async () => {
    apiClientMock.mockResolvedValueOnce({ access_token: 'tok', role: 'user', store_role: 'tenant_admin' })
    const user = userEvent.setup()

    render(<SignupPage />)

    await user.click(screen.getByRole('button', { name: /^seller$/i }))

    expect(screen.getByLabelText(/store name/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/^full name$/i)).not.toBeInTheDocument()

    await user.type(screen.getByLabelText(/store name/i), 'Nike Israel')
    expect(screen.getByLabelText(/store url/i)).toHaveValue('nike-israel')

    await user.type(screen.getByLabelText(/your full name/i), 'Store Owner')
    await user.type(screen.getByLabelText(/email address/i), 'owner@nike.co.il')
    await user.type(screen.getByLabelText(/^password$/i), 'securepass123')
    await user.click(screen.getByRole('button', { name: /create store/i }))

    expect(apiClientMock).toHaveBeenCalledWith('/api/v1/auth/register-tenant', {
      method: 'POST',
      body: JSON.stringify({
        store_name: 'Nike Israel',
        store_slug: 'nike-israel',
        admin_email: 'owner@nike.co.il',
        admin_password: 'securepass123',
        admin_full_name: 'Store Owner',
      }),
    })
    expect(setCookieMock).toHaveBeenCalledWith('token', 'tok', expect.objectContaining({ path: '/' }))
    expect(setCookieMock).toHaveBeenCalledWith('tenantSlug', 'nike-israel', expect.objectContaining({ path: '/' }))
    expect(window.location.assign).toHaveBeenCalledWith('/admin/dashboard')
  })

  it('shows the API error message when registration fails', async () => {
    apiClientMock.mockRejectedValueOnce(new Error('Email already registered. Please log in instead.'))
    const user = userEvent.setup()

    render(<SignupPage />)

    await user.type(screen.getByLabelText(/full name/i), 'Jane Doe')
    await user.type(screen.getByLabelText(/email address/i), 'jane@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'securepass123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByText(/email already registered/i)).toBeInTheDocument()
  })
})
