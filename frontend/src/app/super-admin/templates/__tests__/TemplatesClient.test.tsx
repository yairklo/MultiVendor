import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { TemplatesClient, StorefrontTemplateAdmin } from '../TemplatesClient'

const apiClientMock = vi.fn()
const showToastMock = vi.fn()

vi.mock('@/lib/api/apiClient', () => ({
  apiClient: (...args: unknown[]) => apiClientMock(...args),
}))

vi.mock('@/context/ToastContext', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

const aurora: StorefrontTemplateAdmin = {
  id: 1,
  template_key: 'aurora',
  name: 'Aurora',
  tagline: 'Soft, minimal, boutique-ready.',
  swatch_json: { bg: '#faf8f5', text: '#1f2937', accent: '#6366f1' },
  pages_json: { home: { title: 'Home', sections: [] } },
  display_order: 1,
  is_active: true,
  is_builtin: true,
}

const lumen: StorefrontTemplateAdmin = {
  id: 4,
  template_key: 'lumen',
  name: 'Lumen',
  tagline: 'Bright and airy.',
  swatch_json: { bg: '#ffffff', text: '#111827', accent: '#0ea5e9' },
  pages_json: { home: { title: 'Home', sections: [] } },
  display_order: 10,
  is_active: false,
  is_builtin: false,
}

describe('TemplatesClient', () => {
  beforeEach(() => {
    apiClientMock.mockReset()
    showToastMock.mockReset()
  })

  it('lists active and inactive templates without rewriting tenant management', () => {
    render(<TemplatesClient initialTemplates={[aurora, lumen]} />)

    expect(screen.getByRole('heading', { name: 'Storefront templates' })).toBeInTheDocument()
    expect(screen.getByText('Aurora')).toBeInTheDocument()
    expect(screen.getByText('Lumen')).toBeInTheDocument()
    expect(screen.getByText('Built-in')).toBeInTheDocument()
    expect(screen.getByText('Inactive')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'New template' })).toBeInTheDocument()
  })

  it('deactivates a built-in template instead of deleting it', async () => {
    const user = userEvent.setup()
    apiClientMock.mockResolvedValueOnce({})
    apiClientMock.mockResolvedValueOnce({ data: [{ ...aurora, is_active: false }, lumen] })

    render(<TemplatesClient initialTemplates={[aurora, lumen]} />)

    await user.click(screen.getAllByRole('button', { name: 'Deactivate' })[0])

    expect(apiClientMock).toHaveBeenCalledWith(
      '/api/v1/super-admin/storefront-templates/aurora',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ is_active: false }),
      }),
    )
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument()
  })
})
