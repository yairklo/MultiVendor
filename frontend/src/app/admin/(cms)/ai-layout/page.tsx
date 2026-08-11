'use client'

import React, { useEffect, useState } from 'react'
import { UploadCloud } from 'lucide-react'
import { DraggablePageEditor } from '@/components/admin/ai/DraggablePageEditor'
import { ContextBadge } from '@/components/admin/ai/ContextBadge'
import { ChatDrawer } from '@/components/admin/ai/ChatDrawer'
import { VersionHistoryPanel } from '@/components/admin/ai/VersionHistoryPanel'
import { useAiLayout } from '@/hooks/useAiLayout'
import { useAutoSyncAIContext } from '@/hooks/useAutoSyncAIContext'
import { useToast } from '@/context/ToastContext'
import { useConfirm } from '@/context/ConfirmContext'
import { DispatchedAction, PageType, Section, StorePageSchema, StorePageSummary, StorePageVersionSummary } from '@/lib/ai/types'

export default function AiLayoutPage() {
  const {
    tenantSlug, fetchStatus, fetchPageTargets, fetchPageSchema, sendChatMessage,
    fetchPageVersions, revertToVersion, fetchConversation, clearConversation, publishPage,
    confirmPendingAction, cancelPendingAction, saveLayout,
  } = useAiLayout()
  const { pageKey, pageType, messages, setMessages, setContext } = useAutoSyncAIContext()
  const { showToast } = useToast()
  const { confirm } = useConfirm()

  const [targets, setTargets] = useState<StorePageSummary[]>([])
  const [page, setPage] = useState<StorePageSchema | null>(null)
  const [provider, setProvider] = useState<'gemini' | 'mock' | null>(null)
  const [isBusy, setIsBusy] = useState(false)
  const [versions, setVersions] = useState<StorePageVersionSummary[]>([])
  const [revertingId, setRevertingId] = useState<number | null>(null)
  const [publishing, setPublishing] = useState(false)
  const [resolvingConfirmationId, setResolvingConfirmationId] = useState<string | null>(null)
  const [savingLayout, setSavingLayout] = useState(false)

  useEffect(() => {
    fetchStatus().then((s) => setProvider(s.provider)).catch(() => {})
    fetchPageTargets().then(setTargets).catch((err) => showToast(err.message, 'error'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    setPage(null)
    fetchPageSchema(pageKey, pageType)
      .then(setPage)
      .catch(() => setPage(null)) // page doesn't exist yet — the AI will create it on first edit

    fetchPageVersions(pageKey, pageType).then(setVersions).catch(() => setVersions([]))

    // Restore the real persisted conversation for this page, rather than
    // just showing an empty drawer — the AI genuinely remembers this history too.
    fetchConversation(pageKey, pageType)
      .then((res) => setMessages(res.messages.map((m) => ({ role: m.role, text: m.text, toolCalls: m.tool_calls ?? undefined }))))
      .catch(() => setMessages([]))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageKey, pageType])

  function handleAction(action: DispatchedAction) {
    showToast(`${action.label} → ${action.actionType}`, 'info')
  }

  async function handleSend(message: string) {
    setMessages((prev) => [...prev, { role: 'user', text: message }])
    setIsBusy(true)
    try {
      const result = await sendChatMessage(message, pageKey, pageType)
      setProvider(result.used_provider)
      if (result.page) setPage(result.page)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: result.reply,
          toolCalls: result.tool_calls,
          pendingConfirmation: result.pending_confirmation ?? undefined,
        },
      ])
      fetchPageTargets().then(setTargets).catch(() => {})
      fetchPageVersions(pageKey, pageType).then(setVersions).catch(() => {})
    } catch (err: any) {
      setMessages((prev) => [...prev, { role: 'assistant', text: `Error: ${err.message}` }])
      showToast(err.message || 'Failed to send message', 'error')
    } finally {
      setIsBusy(false)
    }
  }

  function resolvePendingConfirmationInPlace(confirmationId: string, noteText: string) {
    setMessages((prev) =>
      prev.map((m) =>
        m.pendingConfirmation?.id === confirmationId
          ? { ...m, text: `${m.text}\n\n${noteText}`, pendingConfirmation: undefined }
          : m,
      ),
    )
  }

  async function handleConfirmPendingAction(confirmationId: string) {
    setResolvingConfirmationId(confirmationId)
    try {
      await confirmPendingAction(confirmationId)
      resolvePendingConfirmationInPlace(confirmationId, '✅ Confirmed — done.')
      showToast('Action completed.', 'success')
      fetchPageTargets().then(setTargets).catch(() => {})
    } catch (err: any) {
      showToast(err.message || 'Failed to confirm action', 'error')
    } finally {
      setResolvingConfirmationId(null)
    }
  }

  async function handleCancelPendingAction(confirmationId: string) {
    setResolvingConfirmationId(confirmationId)
    try {
      await cancelPendingAction(confirmationId)
      resolvePendingConfirmationInPlace(confirmationId, '❎ Cancelled — nothing was changed.')
    } catch (err: any) {
      showToast(err.message || 'Failed to cancel action', 'error')
    } finally {
      setResolvingConfirmationId(null)
    }
  }

  async function handleNewConversation() {
    try {
      await clearConversation(pageKey, pageType)
      setMessages([])
    } catch (err: any) {
      showToast(err.message || 'Failed to start a new conversation', 'error')
    }
  }

  async function handleRevert(versionId: number) {
    const ok = await confirm({
      title: 'Revert to this version?',
      description: 'The current draft will be saved as a new version first, so this can be undone too.',
      confirmLabel: 'Revert',
      variant: 'destructive',
    })
    if (!ok) return

    setRevertingId(versionId)
    try {
      const reverted = await revertToVersion(pageKey, pageType, versionId)
      setPage(reverted)
      fetchPageVersions(pageKey, pageType).then(setVersions).catch(() => {})
      showToast('Page reverted. Remember to publish if this should go live.', 'success')
    } catch (err: any) {
      showToast(err.message || 'Failed to revert', 'error')
    } finally {
      setRevertingId(null)
    }
  }

  function handleSectionsReorder(sections: Section[]) {
    setPage((prev) => (prev ? { ...prev, sections } : prev))
  }

  async function handleSaveLayout() {
    if (!page) return
    setSavingLayout(true)
    try {
      const saved = await saveLayout(page)
      setPage(saved)
      fetchPageVersions(pageKey, pageType).then(setVersions).catch(() => {})
      showToast('Layout saved. Remember to publish if this should go live.', 'success')
    } catch (err: any) {
      showToast(err.message || 'Failed to save layout', 'error')
    } finally {
      setSavingLayout(false)
    }
  }

  async function handlePublish() {
    const ok = await confirm({
      title: 'Publish this page?',
      description: `This makes the current draft visible to every customer visiting your store — page_key="${pageKey}".`,
      confirmLabel: 'Publish',
    })
    if (!ok) return

    setPublishing(true)
    try {
      const published = await publishPage(pageKey, pageType)
      setPage(published)
      showToast('Published — this is now live on your storefront.', 'success')
    } catch (err: any) {
      showToast(err.message || 'Failed to publish', 'error')
    } finally {
      setPublishing(false)
    }
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <h1 className="text-3xl font-bold text-gray-900">AI Layout & Product Assistant</h1>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex-1">
          <ContextBadge targets={targets} pageKey={pageKey} pageType={pageType} provider={provider} onChange={setContext} />
        </div>
        <VersionHistoryPanel
          versions={versions}
          onRevert={handleRevert}
          revertingId={revertingId}
          publishedAt={page?.published_at}
        />
        <button
          type="button"
          onClick={handlePublish}
          disabled={publishing || !page}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50 ${
            page?.has_unpublished_changes ? 'bg-blue-600 hover:bg-blue-700' : 'bg-gray-300'
          }`}
        >
          <UploadCloud className="h-4 w-4" />
          {publishing ? 'Publishing…' : page?.has_unpublished_changes ? 'Publish' : 'Published'}
        </button>
      </div>

      {page?.has_unpublished_changes && (
        <div className="rounded-lg bg-amber-50 px-4 py-2 text-sm text-amber-700">
          This page has unpublished changes — customers still see the last published version until you publish.
        </div>
      )}

      <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden lg:grid-cols-[1fr_380px]">
        <div
          className="overflow-y-auto rounded-xl border border-gray-100 bg-gray-50 p-6"
          style={{ backgroundColor: page?.background_color || undefined, color: page?.text_color || undefined }}
        >
          <DraggablePageEditor
            page={page}
            onChange={handleSectionsReorder}
            onSave={handleSaveLayout}
            saving={savingLayout}
            tenantSlug={tenantSlug}
            onAction={handleAction}
            showTypeLabels
          />
        </div>
        <div className="min-h-[400px]">
          <ChatDrawer
            messages={messages}
            onSend={handleSend}
            isBusy={isBusy}
            onNewConversation={handleNewConversation}
            onConfirmAction={handleConfirmPendingAction}
            onCancelAction={handleCancelPendingAction}
            resolvingConfirmationId={resolvingConfirmationId}
          />
        </div>
      </div>
    </div>
  )
}
