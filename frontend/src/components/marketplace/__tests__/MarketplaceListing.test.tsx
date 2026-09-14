import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { MarketplaceListing } from '../MarketplaceListing'
import { MarketplaceCartProvider } from '@/context/MarketplaceCartContext'
import { server } from '@/mocks/server'
import type { MarketplaceProduct, MarketplaceCategory } from '@/lib/types'

vi.mock('@/hooks/useCurrency', () => ({
  useCurrency: () => ({
    formatCurrency: (amount: number) => `$${amount}`,
    currency: 'USD',
  }),
}))

const mockCategories: MarketplaceCategory[] = [
  { id: 1, slug: 'coffee', name: { en: 'Coffee', he: 'קפה' }, product_count: 5 },
  { id: 2, slug: 'tea', name: { en: 'Tea', he: 'תה' }, product_count: 3 },
]

const mockProducts: MarketplaceProduct[] = [
  {
    id: 1,
    tenant_id: 1,
    tenant_slug: 'roasters',
    tenant_name: 'Artisan Roasters',
    category_id: 1,
    category_slug: 'coffee',
    category_name: { en: 'Coffee' },
    name: { en: 'Espresso Blend' },
    slug: 'espresso-blend',
    base_price: 18,
    product_type: 'physical',
    images: [],
    variants: [{ id: 101, sku: 'ESP-1', stock_quantity: 10 }],
    review_count: 0,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 2,
    tenant_id: 2,
    tenant_slug: 'teashop',
    tenant_name: 'Herbal Tea House',
    category_id: 2,
    category_slug: 'tea',
    category_name: { en: 'Tea' },
    name: { en: 'Green Tea' },
    slug: 'green-tea',
    base_price: 12,
    product_type: 'physical',
    images: [],
    variants: [{ id: 201, sku: 'TEA-1', stock_quantity: 10 }],
    review_count: 0,
    created_at: '2026-01-02T00:00:00Z',
  },
]

describe('MarketplaceListing', () => {
  let capturedUrl: string | null = null

  beforeEach(() => {
    capturedUrl = null
    server.use(
      http.get('http://localhost:8000/api/v1/marketplace/categories', () => {
        return HttpResponse.json(mockCategories)
      }),
      http.get('http://localhost:8000/api/v1/marketplace/products', ({ request }) => {
        capturedUrl = request.url
        const url = new URL(request.url)
        const category = url.searchParams.get('category')
        if (category === 'coffee') {
          return HttpResponse.json({ data: [mockProducts[0]], meta: { total: 1, page: 1, total_pages: 1 } })
        }
        if (category === 'tea') {
          return HttpResponse.json({ data: [mockProducts[1]], meta: { total: 1, page: 1, total_pages: 1 } })
        }
        return HttpResponse.json({ data: mockProducts, meta: { total: 2, page: 1, total_pages: 1 } })
      })
    )
  })

  it('renders category filter buttons with product counts and All option', () => {
    render(
      <MarketplaceCartProvider>
        <MarketplaceListing
          initialProducts={mockProducts}
          initialCategories={mockCategories}
        />
      </MarketplaceCartProvider>
    )

    expect(screen.getByRole('button', { name: /^all$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /coffee/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /tea/i })).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('filters products when clicking a category pill', async () => {
    const user = userEvent.setup()
    render(
      <MarketplaceCartProvider>
        <MarketplaceListing
          initialProducts={mockProducts}
          initialCategories={mockCategories}
        />
      </MarketplaceCartProvider>
    )

    const coffeeBtn = screen.getByRole('button', { name: /coffee/i })
    await user.click(coffeeBtn)

    await waitFor(() => {
      expect(capturedUrl).toContain('category=coffee')
    })
    expect(await screen.findByText('Espresso Blend')).toBeInTheDocument()
  })

  it('clears the category filter when clicking All', async () => {
    const user = userEvent.setup()
    render(
      <MarketplaceCartProvider>
        <MarketplaceListing
          initialProducts={mockProducts}
          initialCategories={mockCategories}
          initialCategory="coffee"
        />
      </MarketplaceCartProvider>
    )

    const allBtn = screen.getByRole('button', { name: /^all$/i })
    await user.click(allBtn)

    await waitFor(() => {
      expect(capturedUrl).not.toContain('category=')
    })
  })

  it('fetches categories from API if initialCategories was not provided', async () => {
    render(
      <MarketplaceCartProvider>
        <MarketplaceListing initialProducts={mockProducts} />
      </MarketplaceCartProvider>
    )

    expect(await screen.findByRole('button', { name: /coffee/i })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /tea/i })).toBeInTheDocument()
  })
})
