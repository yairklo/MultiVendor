"use client"

import { AlertTriangle, Paperclip, X } from 'lucide-react'
import { FormEvent, KeyboardEvent, useRef, useState } from 'react'
import { ChatMessage } from '@/lib/ai/types'

export function ChatDrawer({
  messages,
  onSend,
  isBusy,
  onNewConversation,
  onConfirmAction,
  onCancelAction,
  resolvingConfirmationId,
  title = 'AI Layout & Product Assistant',
  emptyStateHint = (
    <>
      Try: &ldquo;Make the hero banner larger and move the video above the products&rdquo; or &ldquo;add a
      product called Cool Mug for $15&rdquo;
    </>
  ),
}: {
  messages: ChatMessage[]
  onSend: (message: string, file?: File | null) => void
  isBusy: boolean
  onNewConversation?: () => void
  /** Called with the pending action's id when the user clicks Confirm on a staged destructive action. */
  onConfirmAction?: (confirmationId: string) => void
  onCancelAction?: (confirmationId: string) => void
  /** The confirmation id currently being confirmed/cancelled, so its buttons can show a busy state. */
  resolvingConfirmationId?: string | null
  /** Header text — pass null to omit the header entirely when the page already shows its own title. */
  title?: React.ReactNode | null
  /** Example-prompts shown before the first message — swap for context (page editor vs. general copilot). */
  emptyStateHint?: React.ReactNode
}) {
  const [draft, setDraft] = useState('')
  const [attachedFile, setAttachedFile] = useState<File | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function submitDraft() {
    const trimmed = draft.trim()
    if ((!trimmed && !attachedFile) || isBusy) return
    onSend(trimmed, attachedFile)
    setDraft('')
    setAttachedFile(null)
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    submitDraft()
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submitDraft()
    }
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setIsDragOver(false)
        const file = e.dataTransfer.files?.[0]
        if (file) setAttachedFile(file)
      }}
      className={`relative flex h-full flex-col rounded-xl border bg-white shadow-sm ${
        isDragOver ? 'border-blue-500 ring-2 ring-blue-200' : 'border-gray-100'
      }`}
    >
      {isDragOver && (
        <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-blue-50/90 text-sm font-medium text-blue-700">
          Drop an image or .xlsx file to attach it
        </div>
      )}
      <div className={`flex items-center border-b border-gray-100 px-4 py-3 ${title ? 'justify-between' : 'justify-end'}`}>
        {title && <h3 className="font-bold text-gray-900">{title}</h3>}
        {onNewConversation && messages.length > 0 && (
          <button
            type="button"
            onClick={onNewConversation}
            disabled={isBusy}
            className="text-xs font-medium text-gray-400 hover:text-gray-700 disabled:opacity-50"
          >
            New conversation
          </button>
        )}
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {messages.length === 0 && (
          <div className="rounded-lg bg-gray-50 p-3 text-sm text-gray-500">{emptyStateHint}</div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
            <div
              className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ${
                m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-900'
              }`}
            >
              {m.text}
            </div>
            {m.toolCalls && m.toolCalls.length > 0 && (
              <details className="mt-1 text-xs text-gray-400">
                <summary className="cursor-pointer">{m.toolCalls.length} tool call(s)</summary>
                <ul className="mt-1 space-y-0.5 pl-3">
                  {m.toolCalls.map((tc, j) => (
                    <li key={j}>
                      <code className="rounded bg-gray-100 px-1 py-0.5">{tc.name}</code> {tc.is_error ? '❌' : '✅'}
                    </li>
                  ))}
                </ul>
              </details>
            )}
            {m.pendingConfirmation && (
              <div className="mt-2 max-w-[85%] rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
                <div className="flex gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
                  <p>{m.pendingConfirmation.summary}</p>
                </div>
                <div className="mt-2 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => onCancelAction?.(m.pendingConfirmation!.id)}
                    disabled={resolvingConfirmationId === m.pendingConfirmation.id}
                    className="rounded-lg border border-amber-300 px-3 py-1.5 text-xs font-semibold text-amber-800 hover:bg-amber-100 disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => onConfirmAction?.(m.pendingConfirmation!.id)}
                    disabled={resolvingConfirmationId === m.pendingConfirmation.id}
                    className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
                  >
                    {resolvingConfirmationId === m.pendingConfirmation.id ? 'Working…' : 'Confirm'}
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
        {isBusy && <div className="text-sm text-gray-400">Thinking…</div>}
      </div>

      <form className="flex flex-col gap-2 border-t border-gray-100 p-3" onSubmit={handleSubmit}>
        {attachedFile && (
          <div className="flex w-fit items-center gap-2 rounded-lg bg-gray-100 px-2.5 py-1 text-xs text-gray-700">
            <Paperclip className="h-3.5 w-3.5" />
            <span>{attachedFile.name}</span>
            <button
              type="button"
              onClick={() => setAttachedFile(null)}
              className="text-gray-400 hover:text-gray-700"
              aria-label="Remove attachment"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
        <div className="flex gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.xlsx"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) setAttachedFile(file)
            e.target.value = ''
          }}
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isBusy}
          title="Attach an image or .xlsx spreadsheet"
          className="self-end rounded-lg border px-3 py-2 text-gray-500 hover:bg-gray-50 disabled:opacity-50"
        >
          <Paperclip className="h-4 w-4" />
        </button>
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe a layout change or a product to add… (Shift+Enter for a new line)"
          disabled={isBusy}
          rows={2}
          className="flex-1 max-h-32 min-h-[2.5rem] resize-y overflow-y-auto rounded-lg border px-3 py-2 text-sm focus:ring-2 focus:ring-blue-600 outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isBusy || (!draft.trim() && !attachedFile)}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 self-end"
        >
          Send
        </button>
        </div>
      </form>
    </div>
  )
}
