import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import AdminLayout from '../(cms)/layout'

vi.mock('next/navigation', () => ({
  usePathname: () => '/admin/dashboard',
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}))

// Auth gating for /admin/** now happens in proxy.ts (middleware) before this
// layout ever renders — see src/__tests__/proxy.test.ts. This layout can
// assume it's only ever reached by an authenticated request.
describe('AdminLayout', () => {
  it('renders the nav shell and children', () => {
    render(
      <AdminLayout>
        <div>Protected Content</div>
      </AdminLayout>
    )

    expect(screen.getByText('Protected Content')).toBeInTheDocument()
    expect(screen.getAllByText('Dashboard').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Products').length).toBeGreaterThan(0)
  })
})
