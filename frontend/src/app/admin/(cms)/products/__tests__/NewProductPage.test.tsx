import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import NewProductPage from '../new/page'
import { ApiError } from '@/lib/api/apiClient'

const createProductMock = vi.fn()
const uploadImageMock = vi.fn()
const uploadFileMock = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/hooks/useProducts', () => ({
  useProducts: () => ({ createProduct: createProductMock }),
}))

vi.mock('@/hooks/useUploads', () => ({
  useUploads: () => ({ uploadImage: uploadImageMock, uploadFile: uploadFileMock }),
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

  it('submits product_type digital, zero stock, and the uploaded file URL when the digital checkbox is checked', async () => {
    uploadFileMock.mockResolvedValueOnce({ url: '/uploads/1/files/abc_ebook.pdf' })
    createProductMock.mockResolvedValueOnce({ id: 4 })
    const user = userEvent.setup()

    render(<NewProductPage />)

    await user.type(screen.getByLabelText(/product name \(english\)/i), 'Ebook')
    await user.type(screen.getByLabelText(/product name \(hebrew\)/i), 'ספר')
    await user.type(screen.getByLabelText(/slug/i), 'ebook')
    await user.clear(screen.getByLabelText(/base price/i))
    await user.type(screen.getByLabelText(/base price/i), '19')
    await user.click(screen.getByRole('checkbox', { name: /digital product/i }))

    const file = new File(['%PDF-1.1'], 'ebook.pdf', { type: 'application/pdf' })
    await user.upload(screen.getByLabelText(/product file/i), file)
    await waitFor(() => expect(uploadFileMock).toHaveBeenCalledWith(file))

    await user.click(screen.getByRole('button', { name: /save product/i }))

    expect(createProductMock).toHaveBeenCalledWith(expect.objectContaining({
      product_type: 'digital',
      digital_file_url: '/uploads/1/files/abc_ebook.pdf',
      variants: [expect.objectContaining({ stock_quantity: 0 })],
    }))
  })

  it('uploads a selected file and includes the returned URL in the images array', async () => {
    uploadImageMock.mockResolvedValueOnce({ url: '/uploads/1/products/abc123.png' })
    createProductMock.mockResolvedValueOnce({ id: 3 })
    const user = userEvent.setup()

    render(<NewProductPage />)

    await user.type(screen.getByLabelText(/product name \(english\)/i), 'Uploaded Product')
    await user.type(screen.getByLabelText(/product name \(hebrew\)/i), 'מוצר')
    await user.type(screen.getByLabelText(/slug/i), 'uploaded-product')
    await user.clear(screen.getByLabelText(/base price/i))
    await user.type(screen.getByLabelText(/base price/i), '10')

    const file = new File(['fake-image-bytes'], 'photo.png', { type: 'image/png' })
    const fileInput = screen.getByLabelText(/upload image file/i)
    expect(fileInput).not.toBeDisabled()
    await user.upload(fileInput, file)

    await waitFor(() => expect(uploadImageMock).toHaveBeenCalledWith(file))
    await user.click(screen.getByRole('button', { name: /save product/i }))

    expect(createProductMock).toHaveBeenCalledWith(
      expect.objectContaining({ images: ['/uploads/1/products/abc123.png'] })
    )
  })
})
