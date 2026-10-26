import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { DashboardClient } from '../(cms)/dashboard/DashboardClient'

vi.mock('@/hooks/useCurrency', () => ({
  useCurrency: () => ({
    formatCurrency: (amount: number) => `$${Number(amount).toLocaleString()}`,
    currency: 'USD',
  }),
}))

vi.mock('next/navigation', () => ({
  usePathname: () => '/admin/dashboard',
  useRouter: () => ({ push: vi.fn() }),
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
        categorySales={[]}
        recentOrders={[]}
        lowStockProducts={[]}
        recentReviews={[]}
        rangeDays={30}
      />
    )

    expect(screen.getByText('Total Revenue')).toBeInTheDocument()
    expect(screen.getByText('Average Order Value')).toBeInTheDocument()
    expect(screen.getByText('Total Orders')).toBeInTheDocument()

    expect(screen.getByText('$50,000')).toBeInTheDocument()
    expect(screen.getByText('$125.5')).toBeInTheDocument()
    expect(screen.getByText('400')).toBeInTheDocument()
  })

  it.each([
    [7, 'vs previous 7 days'],
    [30, 'vs previous 30 days'],
    [90, 'vs previous 90 days'],
    [365, 'vs previous year'],
  ] as const)('labels the trend for a %i day range as "%s" and shows the real percentage', (rangeDays, label) => {
    render(
      <DashboardClient
        metrics={{ data: [], total_revenue: 150, aov: 50, orders_count: 3 }}
        previousMetrics={{ data: [], total_revenue: 100, aov: 50, orders_count: 2 }}
        topProducts={[]}
        categorySales={[]}
        recentOrders={[]}
        lowStockProducts={[]}
        recentReviews={[]}
        rangeDays={rangeDays}
      />
    )
    expect(screen.getAllByText(new RegExp(label))).toHaveLength(2)
    expect(screen.getAllByText('+50%')).toHaveLength(2)
    expect(screen.queryByText(/last month/)).not.toBeInTheDocument()
  })

  it('hides the trend when there is no previous period', () => {
    render(
      <DashboardClient
        metrics={{ data: [], total_revenue: 150, aov: 50, orders_count: 3 }}
        previousMetrics={null}
        topProducts={[]}
        categorySales={[]}
        recentOrders={[]}
        lowStockProducts={[]}
        recentReviews={[]}
        rangeDays={30}
      />
    )
    expect(screen.queryByText(/vs previous/)).not.toBeInTheDocument()
  })
})
