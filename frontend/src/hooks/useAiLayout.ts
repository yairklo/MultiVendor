import { apiClient } from '@/lib/api/apiClient'
import { useTenantSlug } from './useTenantSlug'
import {
  AIChatResponse, ConversationResponse, PageContext, PageType, StorePageSchema, StorePageSummary,
  StorePageVersionSummary,
} from '@/lib/ai/types'

/** page_key/page_type query params for a page-scoped request, or nothing for the global copilot. */
function pageContextParams(pageContext: PageContext): Record<string, string> {
  return pageContext ? { page_key: pageContext.pageKey, page_type: pageContext.pageType } : {}
}

export function useAiLayout() {
  const tenantSlug = useTenantSlug()

  const adminPath = (suffix: string) => {
    if (!tenantSlug) throw new Error('Tenant slug is not resolved')
    return `/api/v1/admin/store/${tenantSlug}${suffix}`
  }

  const fetchStatus = async (): Promise<{ provider: 'gemini' | 'mock' }> => {
    return apiClient(adminPath('/ai/status'))
  }

  const fetchPageTargets = async (): Promise<StorePageSummary[]> => {
    return apiClient(adminPath('/ai/page-targets'))
  }

  const fetchPageSchema = async (pageKey: string, pageType: PageType): Promise<StorePageSchema> => {
    const params = new URLSearchParams({ page_key: pageKey, page_type: pageType })
    return apiClient(adminPath(`/ai/page-schema?${params.toString()}`))
  }

  const sendChatMessage = async (
    message: string, pageContext: PageContext, attachedFile?: File | null
  ): Promise<AIChatResponse> => {
    const formData = new FormData()
    formData.append('message', message)
    if (pageContext) {
      formData.append('page_key', pageContext.pageKey)
      formData.append('page_type', pageContext.pageType)
    }
    if (attachedFile) {
      formData.append('file', attachedFile)
    }
    return apiClient(adminPath('/ai/chat'), {
      method: 'POST',
      body: formData,
    })
  }

  const fetchPageVersions = async (pageKey: string, pageType: PageType): Promise<StorePageVersionSummary[]> => {
    const params = new URLSearchParams({ page_key: pageKey, page_type: pageType })
    return apiClient(adminPath(`/ai/page-versions?${params.toString()}`))
  }

  const revertToVersion = async (pageKey: string, pageType: PageType, versionId: number): Promise<StorePageSchema> => {
    const params = new URLSearchParams({ page_key: pageKey, page_type: pageType })
    return apiClient(adminPath(`/ai/page-versions/${versionId}/revert?${params.toString()}`), {
      method: 'POST',
    })
  }

  const fetchConversation = async (pageContext: PageContext): Promise<ConversationResponse> => {
    const params = new URLSearchParams(pageContextParams(pageContext))
    const query = params.toString()
    return apiClient(adminPath(`/ai/conversation${query ? `?${query}` : ''}`))
  }

  const clearConversation = async (pageContext: PageContext): Promise<void> => {
    const params = new URLSearchParams(pageContextParams(pageContext))
    const query = params.toString()
    await apiClient(adminPath(`/ai/conversation${query ? `?${query}` : ''}`), {
      method: 'DELETE',
    })
  }

  const publishPage = async (pageKey: string, pageType: PageType): Promise<StorePageSchema> => {
    const params = new URLSearchParams({ page_key: pageKey, page_type: pageType })
    return apiClient(adminPath(`/ai/publish?${params.toString()}`), {
      method: 'POST',
    })
  }

  const confirmPendingAction = async (confirmationId: string): Promise<any> => {
    return apiClient(adminPath(`/ai/pending-actions/${confirmationId}/confirm`), {
      method: 'POST',
    })
  }

  const cancelPendingAction = async (confirmationId: string): Promise<void> => {
    await apiClient(adminPath(`/ai/pending-actions/${confirmationId}/cancel`), {
      method: 'POST',
    })
  }

  /** Direct write path for manual drag-and-drop reordering — bypasses the AI chat loop entirely. */
  const saveLayout = async (schema: StorePageSchema): Promise<StorePageSchema> => {
    return apiClient(adminPath('/ai/page-schema'), {
      method: 'PUT',
      body: JSON.stringify({
        page_key: schema.page_key,
        page_type: schema.page_type,
        sections: schema.sections,
        title: schema.title,
        background_color: schema.background_color,
        text_color: schema.text_color,
      }),
    })
  }

  const fetchTemplates = async (): Promise<any[]> => {
    return apiClient(adminPath('/ai/templates'))
  }

  const applyTemplate = async (templateKey: string): Promise<any> => {
    return apiClient(adminPath(`/ai/templates/${templateKey}/apply`), {
      method: 'POST',
    })
  }

  return {
    tenantSlug,
    fetchStatus,
    fetchPageTargets,
    fetchPageSchema,
    sendChatMessage,
    fetchPageVersions,
    revertToVersion,
    fetchConversation,
    clearConversation,
    publishPage,
    confirmPendingAction,
    cancelPendingAction,
    saveLayout,
    fetchTemplates,
    applyTemplate,
  }
}
