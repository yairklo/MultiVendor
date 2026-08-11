import { useState } from 'react'
import { ChatMessage, PageType } from '@/lib/ai/types'

/**
 * Holds the {page_key, page_type} the AI chat is currently scoped to, and
 * keeps chat history in sync with it — switching pages starts a fresh
 * conversation instead of carrying context from a different page's edits.
 */
export function useAutoSyncAIContext(initialPageKey = 'home', initialPageType: PageType = 'static_page') {
  const [pageKey, setPageKeyState] = useState(initialPageKey)
  const [pageType, setPageTypeState] = useState<PageType>(initialPageType)
  const [messages, setMessages] = useState<ChatMessage[]>([])

  function setContext(nextPageKey: string, nextPageType: PageType) {
    setPageKeyState(nextPageKey)
    setPageTypeState(nextPageType)
    setMessages([])
  }

  return { pageKey, pageType, messages, setMessages, setContext }
}
