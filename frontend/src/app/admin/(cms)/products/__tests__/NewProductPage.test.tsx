import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import NewProductPage from '../new/page'
import { ApiError } from '@/lib/api/apiClient'

const createProductMock = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/hooks/useProducts', () => ({
  useProducts: () => ({ createProduct: createProductMock }),
}))

describe('NewProductPage subscription limit handling', () => {
  it('shows an upgrade prompt instead of a generic error when the API returns 403', async () => {
    createProductMock.mockRejectedValueOnce(new ApiError(403, 'HTTP Error 403'))
    const user = userEvent.setup()

    render(<NewProductPage />)

    await user.type(screen.getByLabelText(/product name/i), 'Limit Product')
    await user.type(screen.getByLabelText(/slug/i), 'limit-product')
    await user.clear(screen.getByLabelText(/base price/i))
    await user.type(screen.getByLabelText(/base price/i), '10')

    await user.click(screen.getByRole('button', { name: /save product/i }))

    expect(await screen.findByTestId('upgrade-prompt')).toBeInTheDocument()
    expect(screen.getByText(/reached your plan's product limit/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /upgrade plan/i })).toBeInTheDocument()
  })
})
