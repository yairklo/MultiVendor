import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { ImageUploadField } from '../ImageUploadField'

const uploadImageMock = vi.fn()

vi.mock('@/hooks/useUploads', () => ({
  useUploads: () => ({ uploadImage: uploadImageMock }),
}))

describe('ImageUploadField', () => {
  it('renders dropzone when value is empty', () => {
    render(<ImageUploadField value="" onChange={vi.fn()} label="Logo" />)
    expect(screen.getByText('Logo')).toBeInTheDocument()
    expect(screen.getByText(/click or drag an image here/i)).toBeInTheDocument()
  })

  it('shows file attached and remove button when value is present', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()

    render(<ImageUploadField value="/uploads/1/products/logo.png" onChange={onChange} label="Logo" />)
    expect(screen.getByText(/file attached/i)).toBeInTheDocument()
    const removeBtn = screen.getByRole('button', { name: /remove/i })
    expect(removeBtn).toBeInTheDocument()

    await user.click(removeBtn)
    expect(onChange).toHaveBeenCalledWith('')
  })

  it('uploads an image file and calls onChange', async () => {
    uploadImageMock.mockResolvedValueOnce({ url: '/uploads/1/products/test.png' })
    const onChange = vi.fn()
    const user = userEvent.setup()

    render(<ImageUploadField value="" onChange={onChange} label="Logo" id="test-upload" />)

    const file = new File(['fake-bytes'], 'test.png', { type: 'image/png' })
    const input = screen.getByLabelText('Logo')
    await user.upload(input, file)

    await waitFor(() => expect(uploadImageMock).toHaveBeenCalledWith(file))
    expect(onChange).toHaveBeenCalledWith('/uploads/1/products/test.png')
  })

  it('supports URL tab when allowUrlInput is true', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()

    render(<ImageUploadField value="" onChange={onChange} label="Logo" allowUrlInput />)

    const urlTab = screen.getByRole('button', { name: /image url/i })
    await user.click(urlTab)

    const urlInput = screen.getByPlaceholderText('https://example.com/image.png')
    expect(urlInput).toBeInTheDocument()

    await user.type(urlInput, 'https://cdn.example.com/logo.png')
    expect(onChange).toHaveBeenCalled()
  })
})
