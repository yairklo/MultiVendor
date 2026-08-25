import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { TemplatePicker } from '../TemplatePicker'

const templates = [
  {
    key: 'aurora',
    name: 'Aurora',
    tagline: 'Soft, minimal, boutique-ready.',
    swatch: { bg: '#faf8f5', text: '#1f2937', accent: '#6366f1' },
  },
]

describe('TemplatePicker', () => {
  const onApply = vi.fn()

  beforeEach(() => {
    onApply.mockReset()
  })

  it('previews home, about, and contact pages before apply', async () => {
    const user = userEvent.setup()
    render(<TemplatePicker templates={templates} onApply={onApply} isApplying={false} />)

    await user.click(screen.getByRole('button', { name: 'Templates' }))

    expect(screen.getByText('Aurora')).toBeInTheDocument()
    expect(screen.getByTestId('template-page-preview-home')).toBeInTheDocument()
    expect(screen.getByTestId('template-page-preview-about')).toBeInTheDocument()
    expect(screen.getByTestId('template-page-preview-contact')).toBeInTheDocument()
    expect(onApply).not.toHaveBeenCalled()
  })

  it('asks for confirmation that home/about/contact will be overwritten', async () => {
    const user = userEvent.setup()
    render(<TemplatePicker templates={templates} onApply={onApply} isApplying={false} />)

    await user.click(screen.getByRole('button', { name: 'Templates' }))
    await user.click(screen.getByRole('button', { name: 'Apply template to drafts' }))

    expect(screen.getByTestId('template-apply-confirm')).toBeInTheDocument()
    expect(screen.getByText('Apply Template?')).toBeInTheDocument()
    expect(screen.getByText(/Home, About, and Contact/i)).toBeInTheDocument()
    expect(onApply).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByTestId('template-apply-confirm')).not.toBeInTheDocument()
    expect(onApply).not.toHaveBeenCalled()
  })

  it('calls onApply only after the overwrite is confirmed', async () => {
    const user = userEvent.setup()
    render(<TemplatePicker templates={templates} onApply={onApply} isApplying={false} />)

    await user.click(screen.getByRole('button', { name: 'Templates' }))
    await user.click(screen.getByRole('button', { name: 'Apply template to drafts' }))
    await user.click(screen.getByRole('button', { name: 'Apply Template' }))

    expect(onApply).toHaveBeenCalledTimes(1)
    expect(onApply).toHaveBeenCalledWith('aurora')
  })
})
