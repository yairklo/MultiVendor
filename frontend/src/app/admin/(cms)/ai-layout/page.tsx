'use client'

import React, { useEffect, useState } from 'react'
import { UploadCloud } from 'lucide-react'
import { DraggablePageEditor } from '@/components/admin/ai/DraggablePageEditor'
import { ContextBadge } from '@/components/admin/ai/ContextBadge'
import { ChatDrawer } from '@/components/admin/ai/ChatDrawer'
import { VersionHistoryPanel } from '@/components/admin/ai/VersionHistoryPanel'
import { TemplatePicker } from '@/components/admin/ai/TemplatePicker'
import { useAiLayout } from '@/hooks/useAiLayout'
import { useAutoSyncAIContext } from '@/hooks/useAutoSyncAIContext'
import { useToast } from '@/context/ToastContext'
import { useConfirm } from '@/context/ConfirmContext'
import { StorefrontThemeProvider, useStorefrontTheme } from '@/context/StorefrontThemeContext'
import { isRtlLang } from '@/lib/languages'
import { StorefrontHeader } from '@/components/storefront/StorefrontHeader'
import { StorefrontFooter } from '@/components/storefront/StorefrontFooter'
import { useUiLocale } from '@/context/UiLocaleContext'
import { DispatchedAction, Section, StorePageSchema, StorePageSummary, StorePageVersionSummary } from '@/lib/ai/types'

export default function AiLayoutPage() {
  const {
    tenantSlug, fetchStatus, fetchPageTargets, fetchPageSchema, sendChatMessage,
    fetchPageVersions, revertToVersion, fetchConversation, clearConversation, publishPage,
    confirmPendingAction, cancelPendingAction, saveLayout, fetchTemplates, applyTemplate,
  } = useAiLayout()
  const { pageKey, pageType, messages, setMessages, setContext } = useAutoSyncAIContext()
  const { showToast } = useToast()
  const { confirm } = useConfirm()
  const { t } = useUiLocale()

  const [targets, setTargets] = useState<StorePageSummary[]>([])
  const [templates, setTemplates] = useState<any[]>([])
  const [page, setPage] = useState<StorePageSchema | null>(null)
  const [provider, setProvider] = useState<'gemini' | 'mock' | null>(null)
  const [isBusy, setIsBusy] = useState(false)
  const [versions, setVersions] = useState<StorePageVersionSummary[]>([])
  const [revertingId, setRevertingId] = useState<number | null>(null)
  const [publishing, setPublishing] = useState(false)
  const [resolvingConfirmationId, setResolvingConfirmationId] = useState<string | null>(null)
  const [savingLayout, setSavingLayout] = useState(false)
  const [applyingTemplate, setApplyingTemplate] = useState(false)

  useEffect(() => {
    // Skip entirely while tenantSlug is still the placeholder — these requests are
    // guaranteed to 404 and get thrown away the instant the real slug resolves (see
    // useTenantSlug), so firing them just adds console noise for no benefit.
    if (!tenantSlug) return
    // See the cancellation comment on the effect below — same stale-placeholder-response
    // race applies here (a 'test-tenant' request resolving after the real 'store1' one
    // would otherwise clobber good state).
    let cancelled = false
    fetchStatus().then((s) => { if (!cancelled) setProvider(s.provider) }).catch(() => {})
    fetchPageTargets().then((t) => { if (!cancelled) setTargets(t) }).catch((err) => showToast(err.message, 'error'))
    fetchTemplates().then((t) => { if (!cancelled) setTemplates(t) }).catch(() => {})
    return () => { cancelled = true }
    // tenantSlug starts at a deterministic 'test-tenant' placeholder and is swapped for the
    // real cookie-derived value shortly after mount (see useTenantSlug) to avoid an SSR/
    // hydration mismatch — this effect must re-fire when that swap happens, or every fetch
    // above stays permanently scoped to the wrong (placeholder) store.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantSlug])

  useEffect(() => {
    // Skip entirely while tenantSlug is still the placeholder (see the effect above).
    if (!tenantSlug) return
    // tenantSlug flips from the 'test-tenant' placeholder to the real value shortly after
    // mount (see useTenantSlug), which re-fires this effect while the placeholder's own
    // fetches may still be in flight. Without this guard, the stale placeholder request's
    // rejection can resolve AFTER the real one's success and clobber good state back to
    // null/empty — the page gets stuck on "Loading page…" forever even though the real
    // fetch succeeded. Same pattern as StorefrontThemeContext's tenant-config effect.
    let cancelled = false
    setPage(null)
    fetchPageSchema(pageKey, pageType)
      .then((p) => { if (!cancelled) setPage(p) })
      .catch(() => { if (!cancelled) setPage(null) }) // page doesn't exist yet — the AI will create it on first edit

    fetchPageVersions(pageKey, pageType)
      .then((v) => { if (!cancelled) setVersions(v) })
      .catch(() => { if (!cancelled) setVersions([]) })

    // Restore the real persisted conversation for this page, rather than
    // just showing an empty drawer — the AI genuinely remembers this history too.
    fetchConversation({ pageKey, pageType })
      .then((res) => { if (!cancelled) setMessages(res.messages.map((m) => ({ role: m.role, text: m.text, toolCalls: m.tool_calls ?? undefined }))) })
      .catch(() => { if (!cancelled) setMessages([]) })

    return () => { cancelled = true }
    // Same tenantSlug-resolves-after-mount reasoning as the effect above.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageKey, pageType, tenantSlug])

  function handleAction(action: DispatchedAction) {
    showToast(`${action.label} → ${action.actionType}`, 'info')
  }

  async function handleSend(message: string, file?: File | null) {
    setMessages((prev) => [
      ...prev,
      { role: 'user', text: file ? `${message}\n\n[Attached file: ${file.name}]` : message },
    ])
    setIsBusy(true)
    try {
      const result = await sendChatMessage(message, { pageKey, pageType }, file)
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
      showToast(err.message || t('aiLayout.sendFailed'), 'error')
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
      resolvePendingConfirmationInPlace(confirmationId, t('aiLayout.confirmedDone'))
      showToast(t('aiLayout.actionCompleted'), 'success')
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
      resolvePendingConfirmationInPlace(confirmationId, t('aiLayout.cancelledNothing'))
    } catch (err: any) {
      showToast(err.message || 'Failed to cancel action', 'error')
    } finally {
      setResolvingConfirmationId(null)
    }
  }

  async function handleNewConversation() {
    try {
      await clearConversation({ pageKey, pageType })
      setMessages([])
    } catch (err: any) {
      showToast(err.message || 'Failed to start a new conversation', 'error')
    }
  }

  async function handleRevert(versionId: number) {
    const ok = await confirm({
      title: t('aiLayout.revertConfirm'),
      description: t('aiLayout.revertDesc'),
      confirmLabel: t('aiLayout.revert'),
      variant: 'destructive',
    })
    if (!ok) return

    setRevertingId(versionId)
    try {
      const reverted = await revertToVersion(pageKey, pageType, versionId)
      setPage(reverted)
      fetchPageVersions(pageKey, pageType).then(setVersions).catch(() => {})
      showToast(t('aiLayout.reverted'), 'success')
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
      showToast(t('aiLayout.layoutSaved'), 'success')
    } catch (err: any) {
      showToast(err.message || 'Failed to save layout', 'error')
    } finally {
      setSavingLayout(false)
    }
  }

  async function handlePublish() {
    const ok = await confirm({
      title: t('aiLayout.publishConfirm'),
      description: t('aiLayout.publishDesc'),
      confirmLabel: t('aiLayout.publish'),
    })
    if (!ok) return

    setPublishing(true)
    try {
      const published = await publishPage(pageKey, pageType)
      setPage(published)
      showToast(t('aiLayout.publishedLive'), 'success')
    } catch (err: any) {
      showToast(err.message || 'Failed to publish', 'error')
    } finally {
      setPublishing(false)
    }
  }

  async function handleApplyTemplate(templateKey: string) {
    const ok = await confirm({
      title: t('aiLayout.applyTemplate'),
      description: t('aiLayout.applyTemplateDesc'),
      confirmLabel: t('aiLayout.applyTemplateBtn'),
    })
    if (!ok) return

    setApplyingTemplate(true)
    try {
      await applyTemplate(templateKey)
      // Reload the current page draft
      const reloadedPage = await fetchPageSchema(pageKey, pageType)
      setPage(reloadedPage)
      fetchPageVersions(pageKey, pageType).then(setVersions).catch(() => {})
      showToast(t('aiLayout.templateApplied'), 'success')
    } catch (err: any) {
      showToast(err.message || 'Failed to apply template', 'error')
    } finally {
      setApplyingTemplate(false)
    }
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <h1 className="text-3xl font-bold text-gray-900">{t('aiLayout.assistantTitle')}</h1>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex-1">
          <ContextBadge targets={targets} pageKey={pageKey} pageType={pageType} provider={provider} onChange={setContext} />
        </div>
        <TemplatePicker templates={templates} onApply={handleApplyTemplate} isApplying={applyingTemplate} />
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
          {publishing ? t('aiLayout.publishing') : page?.has_unpublished_changes ? t('aiLayout.publish') : t('aiLayout.published')}
        </button>
      </div>

      {page?.has_unpublished_changes && (
        <div className="rounded-lg bg-amber-50 px-4 py-2 text-sm text-amber-700">
          {t('aiLayout.unpublishedHint')}
        </div>
      )}

      <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden lg:grid-cols-[1fr_380px]">
        <div className="overflow-y-auto rounded-xl border border-gray-100 bg-gray-50 flex flex-col shadow-inner">
          <StorefrontThemeProvider tenantSlug={tenantSlug} isAdminPreview>
            <PreviewWrapper
              tenantSlug={tenantSlug}
              page={page}
              handleSend={handleSend}
              handleSectionsReorder={handleSectionsReorder}
              handleSaveLayout={handleSaveLayout}
              savingLayout={savingLayout}
              handleAction={handleAction}
            />
          </StorefrontThemeProvider>
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

function PreviewWrapper({ tenantSlug, page, handleSend, handleSectionsReorder, handleSaveLayout, savingLayout, handleAction }: any) {
  const { lang } = useStorefrontTheme()
  return (
    <div dir={isRtlLang(lang) ? 'rtl' : 'ltr'} className="flex-1 flex flex-col h-full w-full">
      <div className="pointer-events-none sticky top-0 z-10 opacity-75 grayscale-[0.2]">
        <StorefrontHeader tenantSlug={tenantSlug} storeName={tenantSlug} isLoggedIn={false} />
      </div>
      <div
        className="flex-1 p-6 relative z-0"
        style={{ backgroundColor: page?.background_color || undefined, color: page?.text_color || undefined }}
      >
        <DraggablePageEditor
          onAskAI={(id, prompt) => handleSend("For the section with ID '" + id + "': " + prompt)}
          page={page}
          onChange={handleSectionsReorder}
          onSave={handleSaveLayout}
          saving={savingLayout}
          tenantSlug={tenantSlug}
          onAction={handleAction}
          showTypeLabels
        />
      </div>
      <div className="pointer-events-none opacity-75 grayscale-[0.2]">
        <StorefrontFooter tenantSlug={tenantSlug} storeName={tenantSlug} />
      </div>
    </div>
  )
}
