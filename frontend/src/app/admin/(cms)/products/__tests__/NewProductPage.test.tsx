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

    await user.type(screen.getByLabelText(/product name \(english\)/i), 'Limit Product')
    await user.type(screen.getByLabelText(/product name \(hebrew\)/i), 'מוצר')
    await user.type(screen.getByLabelText(/slug/i), 'limit-product')
    await user.clear(screen.getByLabelText(/base price/i))
    await user.type(screen.getByLabelText(/base price/i), '10')

    await user.click(screen.getByRole('button', { name: /save product/i }))

    expect(await screen.findByTestId('upgrade-prompt')).toBeInTheDocument()
    expect(screen.getByText(/reached your plan's product limit/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /upgrade plan/i })).toBeInTheDocument()
  })
})

describe('NewProductPage image upload', () => {
  it('includes the image URL in the images array of the create payload when provided', async () => {
    createProductMock.mockResolvedValueOnce({ id: 1 })
    const user = userEvent.setup()

    render(<NewProductPage />)

    await user.type(screen.getByLabelText(/product name \(english\)/i), 'Vintage Tee')
    await user.type(screen.getByLabelText(/product name \(hebrew\)/i), 'חולצה וינטג')
    await user.type(screen.getByLabelText(/slug/i), 'vintage-tee')
    await user.clear(screen.getByLabelText(/base price/i))
    await user.type(screen.getByLabelText(/base price/i), '10')
    await user.type(screen.getByLabelText(/image url/i), 'https://example.com/vintage-tee.jpg')

    await user.click(screen.getByRole('button', { name: /save product/i }))

    expect(createProductMock).toHaveBeenCalledWith(
      expect.objectContaining({ images: ['https://example.com/vintage-tee.jpg'] })
    )
  })

  it('submits an empty images array when no image URL is provided', async () => {
    createProductMock.mockResolvedValueOnce({ id: 2 })
    const user = userEvent.setup()

    render(<NewProductPage />)

    await user.type(screen.getByLabelText(/product name \(english\)/i), 'No Image Product')
    await user.type(screen.getByLabelText(/product name \(hebrew\)/i), 'מוצר')
    await user.type(screen.getByLabelText(/slug/i), 'no-image-product')
    await user.clear(screen.getByLabelText(/base price/i))
    await user.type(screen.getByLabelText(/base price/i), '10')

    await user.click(screen.getByRole('button', { name: /save product/i }))

    expect(createProductMock).toHaveBeenCalledWith(expect.objectContaining({ images: [] }))
  })

  it('shows a disabled file upload input marked as not yet supported by the backend', () => {
    render(<NewProductPage />)
    const fileInput = screen.getByLabelText(/upload image file/i)
    expect(fileInput).toBeDisabled()
    expect(screen.getByText(/requires backend storage support/i)).toBeInTheDocument()
  })
})
