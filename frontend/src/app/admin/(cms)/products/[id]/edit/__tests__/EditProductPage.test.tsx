import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { EditProductClient } from '../EditProductClient'

const updateProductMock = vi.fn()
const pushMock = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock }),
}))

vi.mock('@/hooks/useProducts', () => ({
  useProducts: () => ({ updateProduct: updateProductMock, updateVariant: vi.fn() }),
}))

// The product fetch (app/admin/(cms)/products/[id]/edit/page.tsx) now happens
// server-side in an async Server Component and isn't renderable with RTL —
// this exercises EditProductClient, the client form it feeds with the
// already-fetched product as props.
describe('EditProductClient', () => {
  it('prefills the form with the given product and submits an update', async () => {
    updateProductMock.mockResolvedValueOnce({})
    const user = userEvent.setup()

    render(
      <EditProductClient
        productId="7"
        categories={[]}
        initialSlug="existing-product"
        initialVariant={null}
        initialValues={{
          name_en: 'Existing Product',
          name_he: 'מוצר קיים',
          description_en: 'Old description',
          description_he: '',
          image_url: '',
          base_price: 40,
          category_id: null,
          stock_quantity: 0,
          is_active: true,
        }}
      />
    )

    const nameInput = screen.getByLabelText(/product name \(english\)/i)
    expect(nameInput).toHaveValue('Existing Product')
    expect(screen.getByLabelText(/product name \(hebrew\)/i)).toHaveValue('מוצר קיים')
    expect(screen.getByLabelText(/base price/i)).toHaveValue(40)
    expect(screen.getByDisplayValue('existing-product')).toBeDisabled()

    await user.clear(nameInput)
    await user.type(nameInput, 'Renamed Product')
    await user.click(screen.getByRole('button', { name: /save product/i }))

    expect(updateProductMock).toHaveBeenCalledWith(7, expect.objectContaining({
      name: { en: 'Renamed Product', he: 'מוצר קיים' },
    }))
    expect(pushMock).toHaveBeenCalledWith('/admin/products')
  })
})

describe('EditProductClient image upload', () => {
  it('pre-fills the image URL input from the product\'s primary image', async () => {
    render(
      <EditProductClient
        productId="8"
        categories={[]}
        initialSlug="product-with-image"
        initialVariant={null}
        initialValues={{
          name_en: 'Product With Image',
          name_he: 'מוצר עם תמונה',
          description_en: '',
          description_he: '',
          image_url: 'https://example.com/existing.jpg',
          base_price: 20,
          category_id: null,
          stock_quantity: 0,
          is_active: true,
        }}
      />
    )

    const imageInput = screen.getByLabelText(/image url/i)
    expect(imageInput).toHaveValue('https://example.com/existing.jpg')
  })

  it('leaves the image URL input blank when the product has no image', async () => {
    render(
      <EditProductClient
        productId="9"
        categories={[]}
        initialSlug="product-without-image"
        initialVariant={null}
        initialValues={{
          name_en: 'Product Without Image',
          name_he: 'מוצר בלי תמונה',
          description_en: '',
          description_he: '',
          image_url: '',
          base_price: 20,
          category_id: null,
          stock_quantity: 0,
          is_active: true,
        }}
      />
    )

    const imageInput = screen.getByLabelText(/image url/i)
    expect(imageInput).toHaveValue('')
  })
})
