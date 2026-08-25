import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { TenantsClient } from '../TenantsClient'
import type { SubscriptionPlanAdmin, TenantAdmin } from '../../types'

const apiClientMock = vi.fn()
const showToastMock = vi.fn()
const confirmMock = vi.fn()

vi.mock('@/lib/api/apiClient', () => ({
  apiClient: (...args: unknown[]) => apiClientMock(...args),
}))

vi.mock('@/context/ToastContext', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

vi.mock('@/context/ConfirmContext', () => ({
  useConfirm: () => ({ confirm: confirmMock }),
}))

const plans: SubscriptionPlanAdmin[] = [
  {
    id: 1,
    code: 'free',
    name: 'Free Plan',
    price_monthly: 0,
    max_products: 50,
    max_storage_mb: 500,
    features_json: {},
    tenant_count: 1,
  },
]

const storeA: TenantAdmin = {
  id: 1,
  name: 'Store A',
  slug: 'tenant-a',
  status: 'active',
  plan_id: 1,
  plan_code: 'free',
  plan_name: 'Free Plan',
  max_products: 50,
  product_count: 3,
  custom_domain: null,
  show_all_products_in_marketplace: true,
  stripe_connected: false,
  created_at: '2026-01-01T00:00:00Z',
}

describe('TenantsClient', () => {
  beforeEach(() => {
    apiClientMock.mockReset()
    showToastMock.mockReset()
    confirmMock.mockReset()
  })

  it('lists tenant plan, product usage, and marketplace state', () => {
    render(<TenantsClient initialTenants={[storeA]} plans={plans} />)

    expect(screen.getByRole('heading', { name: 'Tenants' })).toBeInTheDocument()
    expect(screen.getByText('Store A')).toBeInTheDocument()
    expect(screen.getByText(/3 \/ 50/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Listed' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Suspend' })).toBeInTheDocument()
  })

  it('suspends a tenant with the status query param', async () => {
    const user = userEvent.setup()
    confirmMock.mockResolvedValueOnce(true)
    apiClientMock.mockResolvedValueOnce({})
    apiClientMock.mockResolvedValueOnce({ data: [{ ...storeA, status: 'suspended' }] })

    render(<TenantsClient initialTenants={[storeA]} plans={plans} />)
    await user.click(screen.getByRole('button', { name: 'Suspend' }))

    expect(apiClientMock).toHaveBeenCalledWith(
      '/api/v1/super-admin/tenants/1/status?status=suspended',
      expect.objectContaining({ method: 'PATCH' }),
    )
  })

  it('does not suspend when the confirmation is declined', async () => {
    const user = userEvent.setup()
    confirmMock.mockResolvedValueOnce(false)

    render(<TenantsClient initialTenants={[storeA]} plans={plans} />)
    await user.click(screen.getByRole('button', { name: 'Suspend' }))

    expect(apiClientMock).not.toHaveBeenCalled()
  })
})
