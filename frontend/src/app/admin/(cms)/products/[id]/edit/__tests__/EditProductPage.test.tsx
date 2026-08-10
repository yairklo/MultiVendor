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

    const nameInput = await screen.findByLabelText(/product name/i)
    expect(nameInput).toHaveValue('Existing Product')
    expect(screen.getByLabelText(/base price/i)).toHaveValue(40)
    expect(screen.getByDisplayValue('existing-product')).toBeDisabled()

    await user.clear(nameInput)
    await user.type(nameInput, 'Renamed Product')
    await user.click(screen.getByRole('button', { name: /save product/i }))

    expect(updateProductMock).toHaveBeenCalledWith('7', expect.objectContaining({
      name: { en: 'Renamed Product', he: 'Renamed Product' },
    }))
    expect(pushMock).toHaveBeenCalledWith('/admin/products')
  })
})
