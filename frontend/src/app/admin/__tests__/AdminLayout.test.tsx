import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, afterEach } from 'vitest'
import { setCookie, deleteCookie } from 'cookies-next'
import AdminLayout from '../(cms)/layout'

const replaceMock = vi.fn()

vi.mock('next/navigation', () => ({
  usePathname: () => '/admin/dashboard',
  useRouter: () => ({ replace: replaceMock, push: vi.fn() }),
}))

describe('AdminLayout auth guard', () => {
  afterEach(() => {
    deleteCookie('token')
    replaceMock.mockClear()
  })

  it('redirects to /admin/login when no token cookie is present', async () => {
    render(
      <AdminLayout>
        <div>Protected Content</div>
      </AdminLayout>
    )

    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith('/admin/login'))
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  it('renders children when a token cookie is present', async () => {
    setCookie('token', 'valid-token')

    render(
      <AdminLayout>
        <div>Protected Content</div>
      </AdminLayout>
    )

    expect(await screen.findByText('Protected Content')).toBeInTheDocument()
    expect(replaceMock).not.toHaveBeenCalled()
  })
})
