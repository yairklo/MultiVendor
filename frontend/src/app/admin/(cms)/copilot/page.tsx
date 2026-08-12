'use client'

import React, { useEffect, useState } from 'react'
import { ChatDrawer } from '@/components/admin/ai/ChatDrawer'
import { useAiLayout } from '@/hooks/useAiLayout'
import { useToast } from '@/context/ToastContext'

export default function CopilotPage() {
  const { fetchConversation, sendChatMessage, clearConversation, confirmPendingAction, cancelPendingAction } = useAiLayout()
  const { showToast } = useToast()
  
  const [messages, setMessages] = useState<any[]>([])
  const [isBusy, setIsBusy] = useState(false)
  const [resolvingConfirmationId, setResolvingConfirmationId] = useState<string | null>(null)
  
  const GLOBAL_KEY = 'global'
  const GLOBAL_TYPE = 'general' as any

  useEffect(() => {
    fetchConversation(GLOBAL_KEY, GLOBAL_TYPE)
      .then((res) => setMessages(res.messages.map((m: any) => ({ role: m.role, text: m.text, toolCalls: m.tool_calls ?? undefined }))))
      .catch(() => setMessages([]))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleSend(message: string) {
    setMessages((prev) => [...prev, { role: 'user', text: message }])
    setIsBusy(true)
    try {
      const result = await sendChatMessage(message, GLOBAL_KEY, GLOBAL_TYPE)
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
      await clearConversation(GLOBAL_KEY, GLOBAL_TYPE)
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
        />
      </div>
    </div>
  )
}
