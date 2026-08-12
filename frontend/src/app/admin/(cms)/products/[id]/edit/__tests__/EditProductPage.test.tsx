import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import EditProductPage from '../page'

const fetchProductMock = vi.fn()
const updateProductMock = vi.fn()
const pushMock = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock }),
}))

vi.mock('@/hooks/useProducts', () => ({
  useProducts: () => ({ fetchProduct: fetchProductMock, updateProduct: updateProductMock }),
}))

describe('EditProductPage', () => {
  it('prefills the form with the fetched product and submits an update', async () => {
    fetchProductMock.mockResolvedValueOnce({
      id: 7,
      slug: 'existing-product',
      name: { en: 'Existing Product', he: 'מוצר קיים' },
      description: { en: 'Old description', he: 'תיאור ישן' },
      base_price: '40.00',
      category_id: null,
      is_active: true,
    })
    updateProductMock.mockResolvedValueOnce({})
    const user = userEvent.setup()

    render(<EditProductPage params={{ id: '7' }} />)

    const nameInput = await screen.findByLabelText(/product name \(english\)/i)
    expect(nameInput).toHaveValue('Existing Product')
    expect(screen.getByLabelText(/product name \(hebrew\)/i)).toHaveValue('מוצר קיים')
    expect(screen.getByLabelText(/base price/i)).toHaveValue(40)
    expect(screen.getByDisplayValue('existing-product')).toBeDisabled()

    await user.clear(nameInput)
    await user.type(nameInput, 'Renamed Product')
    await user.click(screen.getByRole('button', { name: /save product/i }))

    expect(updateProductMock).toHaveBeenCalledWith('7', expect.objectContaining({
      name: { en: 'Renamed Product', he: 'מוצר קיים' },
    }))
    expect(pushMock).toHaveBeenCalledWith('/admin/products')
  })
})

describe('EditProductPage image upload', () => {
  it('pre-fills the image URL input from the product\'s primary image', async () => {
    fetchProductMock.mockResolvedValueOnce({
      id: 8,
      slug: 'product-with-image',
      name: { en: 'Product With Image', he: 'מוצר עם תמונה' },
      description: null,
      base_price: '20.00',
      category_id: null,
      is_active: true,
      primary_image_url: 'https://example.com/existing.jpg',
      images: ['https://example.com/existing.jpg'],
    })

    render(<EditProductPage params={{ id: '8' }} />)

    const imageInput = await screen.findByLabelText(/image url/i)
    expect(imageInput).toHaveValue('https://example.com/existing.jpg')
  })

  it('leaves the image URL input blank when the product has no image', async () => {
    fetchProductMock.mockResolvedValueOnce({
      id: 9,
      slug: 'product-without-image',
      name: { en: 'Product Without Image', he: 'מוצר בלי תמונה' },
      description: null,
      base_price: '20.00',
      category_id: null,
      is_active: true,
      primary_image_url: null,
      images: [],
    })

    render(<EditProductPage params={{ id: '9' }} />)

    const imageInput = await screen.findByLabelText(/image url/i)
    expect(imageInput).toHaveValue('')
  })
})
