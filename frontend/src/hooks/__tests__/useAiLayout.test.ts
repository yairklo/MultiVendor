import { renderHook } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAiLayout } from '../useAiLayout'

const apiClientMock = vi.fn()

vi.mock('@/lib/api/apiClient', () => ({
  apiClient: (...args: unknown[]) => apiClientMock(...args),
}))

vi.mock('../useTenantSlug', () => ({
  useTenantSlug: () => 'test-tenant',
  PLACEHOLDER_TENANT_SLUG: '',
}))

// useAiLayout now resolves tenantSlug via useTenantSlug (real useState/useEffect, to avoid
// an SSR/hydration mismatch on the real app -- see that hook's own comment), so it must be
// rendered through React via renderHook rather than called as a plain function.
describe('useAiLayout — page-scoped vs. global copilot requests', () => {
  beforeEach(() => {
    apiClientMock.mockReset()
    apiClientMock.mockResolvedValue({})
  })

  it('sendChatMessage omits page_key/page_type when pageContext is null (global copilot)', async () => {
    const { result } = renderHook(() => useAiLayout())
    await result.current.sendChatMessage('how many orders this week', null)

    expect(apiClientMock).toHaveBeenCalledTimes(1)
    const [url, options] = apiClientMock.mock.calls[0]
    expect(url).toContain('/ai/chat')
    const body = options.body as FormData
    expect(body.get('message')).toBe('how many orders this week')
    expect(body.get('page_key')).toBeNull()
    expect(body.get('page_type')).toBeNull()
    expect(body.get('file')).toBeNull()
  })

  it('sendChatMessage includes page_key/page_type when a real page context is given', async () => {
    const { result } = renderHook(() => useAiLayout())
    await result.current.sendChatMessage('add a hero banner', { pageKey: 'home', pageType: 'static_page' })

    const [, options] = apiClientMock.mock.calls[0]
    const body = options.body as FormData
    expect(body.get('message')).toBe('add a hero banner')
    expect(body.get('page_key')).toBe('home')
    expect(body.get('page_type')).toBe('static_page')
  })

  it('fetchConversation hits the bare /conversation endpoint (no query string) when pageContext is null', async () => {
    const { result } = renderHook(() => useAiLayout())
    await result.current.fetchConversation(null)

    const [url] = apiClientMock.mock.calls[0]
    expect(url).toMatch(/\/ai\/conversation$/)
    expect(url).not.toContain('page_key')
    expect(url).not.toContain('page_type')
  })

  it('fetchConversation includes page_key/page_type as query params for a real page', async () => {
    const { result } = renderHook(() => useAiLayout())
    await result.current.fetchConversation({ pageKey: 'about', pageType: 'static_page' })

    const [url] = apiClientMock.mock.calls[0]
    expect(url).toContain('page_key=about')
    expect(url).toContain('page_type=static_page')
  })

  it('clearConversation DELETEs the bare endpoint when pageContext is null', async () => {
    const { result } = renderHook(() => useAiLayout())
    await result.current.clearConversation(null)

    const [url, options] = apiClientMock.mock.calls[0]
    expect(url).toMatch(/\/ai\/conversation$/)
    expect(options.method).toBe('DELETE')
  })
})
