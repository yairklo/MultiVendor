import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import CopilotPage from '../page'

const fetchConversationMock = vi.fn()
const sendChatMessageMock = vi.fn()
const clearConversationMock = vi.fn()
const showToastMock = vi.fn()

vi.mock('@/hooks/useAiLayout', () => ({
  useAiLayout: () => ({
    fetchConversation: fetchConversationMock,
    sendChatMessage: sendChatMessageMock,
    clearConversation: clearConversationMock,
    confirmPendingAction: vi.fn(),
    cancelPendingAction: vi.fn(),
  }),
}))

vi.mock('@/context/ToastContext', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

describe('CopilotPage — the tenant-wide global copilot, not scoped to any page', () => {
  beforeEach(() => {
    fetchConversationMock.mockReset().mockResolvedValue({ messages: [] })
    sendChatMessageMock.mockReset().mockResolvedValue({ reply: 'Sure thing.', tool_calls: [], used_provider: 'mock' })
    clearConversationMock.mockReset().mockResolvedValue(undefined)
  })

  it('loads the conversation with no page context (null), never a fake page_key', async () => {
    render(<CopilotPage />)
    await waitFor(() => expect(fetchConversationMock).toHaveBeenCalledWith(null))
  })

  it('sends chat messages with no page context', async () => {
    const user = userEvent.setup()
    render(<CopilotPage />)
    await waitFor(() => expect(fetchConversationMock).toHaveBeenCalled())

    const textbox = screen.getByPlaceholderText(/Describe a layout change/)
    await user.type(textbox, 'how many orders this week')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(sendChatMessageMock).toHaveBeenCalledWith('how many orders this week', null))
  })

  it('clears the global conversation with no page context on "New conversation"', async () => {
    fetchConversationMock.mockResolvedValue({ messages: [{ role: 'user', text: 'hi', tool_calls: null }] })
    const user = userEvent.setup()
    render(<CopilotPage />)

    const newConvoButton = await screen.findByText('New conversation')
    await user.click(newConvoButton)

    await waitFor(() => expect(clearConversationMock).toHaveBeenCalledWith(null))
  })

  it('does not render the page-editor\'s ChatDrawer header, avoiding duplicate/mismatched branding', async () => {
    render(<CopilotPage />)
    expect(screen.getByRole('heading', { name: 'AI Copilot' })).toBeInTheDocument()
    // The drawer's own default header text must not also appear underneath it.
    expect(screen.queryByText('AI Layout & Product Assistant')).not.toBeInTheDocument()
  })
})
