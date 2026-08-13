import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { DashboardClient } from '../(cms)/dashboard/DashboardClient'

vi.mock('@/hooks/useCurrency', () => ({
  useCurrency: () => ({
    formatCurrency: (amount: number) => `$${Number(amount).toLocaleString()}`,
    currency: 'USD',
  }),
}))

// Data fetching for the dashboard now happens server-side in
// admin/(cms)/dashboard/page.tsx (an async Server Component, not renderable
// with RTL) — this exercises the client presentation component it feeds.
describe('Admin Dashboard', () => {
  it('renders KPI cards using the provided metrics', () => {
    render(
      <DashboardClient
        metrics={{ data: [], total_revenue: 50000, aov: 125.5, orders_count: 400 }}
        topProducts={[]}
        recentOrders={[]}
        lowStockProducts={[]}
        recentReviews={[]}
      />
    )

    expect(screen.getByText('Total Revenue')).toBeInTheDocument()
    expect(screen.getByText('Average Order Value')).toBeInTheDocument()
    expect(screen.getByText('Total Orders')).toBeInTheDocument()

    expect(screen.getByText('$50,000')).toBeInTheDocument()
    expect(screen.getByText('$125.5')).toBeInTheDocument()
    expect(screen.getByText('400')).toBeInTheDocument()
  })
})
