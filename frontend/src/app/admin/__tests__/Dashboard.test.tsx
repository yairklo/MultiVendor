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
          totalRevenue: 50000,
          aov: 125.5,
          ordersCount: 400
        })
      })
    )
  })

  it('renders KPI cards using API response data', async () => {
    render(<Dashboard />)
    expect(await screen.findByText(/Total Revenue/i)).toBeInTheDocument()
    expect(await screen.findByText(/AOV/i)).toBeInTheDocument()
    expect(await screen.findByText(/Orders Count/i)).toBeInTheDocument()
    
    expect(await screen.findByText(/\$50000/)).toBeInTheDocument()
    expect(await screen.findByText(/\$125\.5/)).toBeInTheDocument()
    expect(await screen.findByText(/400/)).toBeInTheDocument()
  })
})

