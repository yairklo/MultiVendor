import { render, screen } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import Dashboard from '../(cms)/dashboard/page'
import { http, HttpResponse } from 'msw'
import { server } from '../../../mocks/server'

describe('Admin Dashboard', () => {
  beforeEach(() => {
      server.use(
        http.get('http://localhost:8000/api/v1/admin/store/:slug/analytics', () => {
          return HttpResponse.json({
            data: [],
            total_revenue: 50000,
            aov: 125.5,
            orders_count: 400
          })
        }),
        http.get('http://localhost:8000/api/v1/admin/store/:slug/analytics/top-products', () => HttpResponse.json([])),
        http.get('http://localhost:8000/api/v1/admin/store/:slug/orders', () => HttpResponse.json([])),
        http.get('http://localhost:8000/api/v1/store/:slug/products', () => HttpResponse.json({ data: [] })),
        http.get('http://localhost:8000/api/v1/admin/store/:slug/reviews', () => HttpResponse.json([]))
      )
  })

  it('renders KPI cards using API response data', async () => {
    render(<Dashboard />)
    expect(await screen.findByText(/Total Revenue/i)).toBeInTheDocument()
    expect(await screen.findByText(/Average Order Value/i)).toBeInTheDocument()
    expect(await screen.findByText(/Total Orders/i)).toBeInTheDocument()
    
    expect(await screen.findByText(/\$50,000/)).toBeInTheDocument()
    expect(await screen.findByText(/\$125\.5/)).toBeInTheDocument()
    expect(await screen.findByText(/400/)).toBeInTheDocument()
  })
})

