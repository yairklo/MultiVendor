import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ChatDrawer } from '../ChatDrawer'

const noop = vi.fn()

describe('ChatDrawer — context-appropriate branding', () => {
  it('shows the default page-editor header and hint when no title/hint override is given', () => {
    render(<ChatDrawer messages={[]} onSend={noop} isBusy={false} />)
    expect(screen.getByText('AI Layout & Product Assistant')).toBeInTheDocument()
    expect(screen.getByText(/Make the hero banner larger/)).toBeInTheDocument()
  })

  it('omits the header entirely when title is null (global copilot has its own page <h1>)', () => {
    render(<ChatDrawer messages={[]} onSend={noop} isBusy={false} title={null} />)
    expect(screen.queryByText('AI Layout & Product Assistant')).not.toBeInTheDocument()
  })

  it('renders a custom emptyStateHint instead of the page-editor example', () => {
    render(
      <ChatDrawer
        messages={[]}
        onSend={noop}
        isBusy={false}
        title={null}
        emptyStateHint={<>Try: &ldquo;how many orders came in this week&rdquo;</>}
      />
    )
    expect(screen.getByText(/how many orders came in this week/)).toBeInTheDocument()
    expect(screen.queryByText(/Make the hero banner larger/)).not.toBeInTheDocument()
  })
})
