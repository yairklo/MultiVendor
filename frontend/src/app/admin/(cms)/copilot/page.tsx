'use client'

import React, { useEffect, useState } from 'react'
import { ChatDrawer } from '@/components/admin/ai/ChatDrawer'
import { useAiLayout } from '@/hooks/useAiLayout'
import { useToast } from '@/context/ToastContext'

// This chat is not scoped to any page — it's the tenant-wide global copilot.
// PageContext is `null` throughout: never fake a page identity to satisfy an
// API shaped for the per-page layout editor.
const NO_PAGE_CONTEXT = null

export default function CopilotPage() {
  const { tenantSlug, fetchConversation, sendChatMessage, clearConversation, confirmPendingAction, cancelPendingAction } = useAiLayout()
  const { showToast } = useToast()

  const [messages, setMessages] = useState<any[]>([])
  const [isBusy, setIsBusy] = useState(false)
  const [resolvingConfirmationId, setResolvingConfirmationId] = useState<string | null>(null)

  useEffect(() => {
    if (!tenantSlug) return
    fetchConversation(NO_PAGE_CONTEXT)
      .then((res) => setMessages(res.messages.map((m: any) => ({ role: m.role, text: m.text, toolCalls: m.tool_calls ?? undefined }))))
      .catch(() => setMessages([]))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantSlug])

  async function handleSend(message: string, file?: File | null) {
    setMessages((prev) => [
      ...prev,
      { role: 'user', text: file ? `${message}\n\n[Attached file: ${file.name}]` : message },
    ])
    setIsBusy(true)
    try {
      const result = await sendChatMessage(message, NO_PAGE_CONTEXT, file)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: result.reply,
          toolCalls: result.tool_calls,
          pendingConfirmation: result.pending_confirmation ?? undefined,
        },
      ])
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
      await clearConversation(NO_PAGE_CONTEXT)
      setMessages([])
    } catch (err: any) {
      showToast(err.message || 'Failed to start a new conversation', 'error')
    }
  }

  return (
    <div className="flex h-full flex-col gap-4 max-w-4xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">AI Copilot</h1>
        <p className="text-gray-500 mt-2">
          Your general assistant for managing inventory, viewing orders, and answering questions about your store.
        </p>
      </div>

      <div className="flex-1 min-h-[500px] border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
        <ChatDrawer
          messages={messages}
          onSend={handleSend}
          isBusy={isBusy}
          onNewConversation={handleNewConversation}
          onConfirmAction={handleConfirmPendingAction}
          onCancelAction={handleCancelPendingAction}
          resolvingConfirmationId={resolvingConfirmationId}
          title={null}
          emptyStateHint={
            <>
              Try: &ldquo;how many orders came in this week&rdquo; or &ldquo;add a product called Cool Mug for
              $15&rdquo;
            </>
          }
        />
      </div>
    </div>
  )
}
