import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAiLayout } from '../useAiLayout'

const apiClientMock = vi.fn()

vi.mock('@/lib/api/apiClient', () => ({
  apiClient: (...args: unknown[]) => apiClientMock(...args),
}))

// The hook is plain functions/closures over getCookie — no React state — so it's
// safe to call directly without renderHook.
describe('useAiLayout — page-scoped vs. global copilot requests', () => {
  beforeEach(() => {
    apiClientMock.mockReset()
    apiClientMock.mockResolvedValue({})
  })

  it('sendChatMessage omits page_key/page_type when pageContext is null (global copilot)', async () => {
    const { sendChatMessage } = useAiLayout()
    await sendChatMessage('how many orders this week', null)

    expect(apiClientMock).toHaveBeenCalledTimes(1)
    const [url, options] = apiClientMock.mock.calls[0]
    expect(url).toContain('/ai/chat')
    const body = JSON.parse(options.body)
    expect(body).toEqual({ message: 'how many orders this week', page_key: null, page_type: null })
  })

  it('sendChatMessage includes page_key/page_type when a real page context is given', async () => {
    const { sendChatMessage } = useAiLayout()
    await sendChatMessage('add a hero banner', { pageKey: 'home', pageType: 'static_page' })

    const [, options] = apiClientMock.mock.calls[0]
    const body = JSON.parse(options.body)
    expect(body).toEqual({ message: 'add a hero banner', page_key: 'home', page_type: 'static_page' })
  })

  it('fetchConversation hits the bare /conversation endpoint (no query string) when pageContext is null', async () => {
    const { fetchConversation } = useAiLayout()
    await fetchConversation(null)

    const [url] = apiClientMock.mock.calls[0]
    expect(url).toMatch(/\/ai\/conversation$/)
    expect(url).not.toContain('page_key')
    expect(url).not.toContain('page_type')
  })

  it('fetchConversation includes page_key/page_type as query params for a real page', async () => {
    const { fetchConversation } = useAiLayout()
    await fetchConversation({ pageKey: 'about', pageType: 'static_page' })

    const [url] = apiClientMock.mock.calls[0]
    expect(url).toContain('page_key=about')
    expect(url).toContain('page_type=static_page')
  })

  it('clearConversation DELETEs the bare endpoint when pageContext is null', async () => {
    const { clearConversation } = useAiLayout()
    await clearConversation(null)

    const [url, options] = apiClientMock.mock.calls[0]
    expect(url).toMatch(/\/ai\/conversation$/)
    expect(options.method).toBe('DELETE')
  })
})
