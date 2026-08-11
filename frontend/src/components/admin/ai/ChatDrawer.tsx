import { FormEvent, useState } from 'react'
import { ChatMessage } from '@/lib/ai/types'

export function ChatDrawer({
  messages,
  onSend,
  isBusy,
  onNewConversation,
}: {
  messages: ChatMessage[]
  onSend: (message: string) => void
  isBusy: boolean
  onNewConversation?: () => void
}) {
  const [draft, setDraft] = useState('')

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = draft.trim()
    if (!trimmed || isBusy) return
    onSend(trimmed)
    setDraft('')
  }

  return (
    <div className="flex h-full flex-col rounded-xl border border-gray-100 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
        <h3 className="font-bold text-gray-900">AI Layout & Product Assistant</h3>
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
          <div className="rounded-lg bg-gray-50 p-3 text-sm text-gray-500">
            Try: &ldquo;Make the hero banner larger and move the video above the products&rdquo; or &ldquo;add a
            product called Cool Mug for $15&rdquo;
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
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
          </div>
        ))}
        {isBusy && <div className="text-sm text-gray-400">Thinking…</div>}
      </div>

      <form className="flex gap-2 border-t border-gray-100 p-3" onSubmit={handleSubmit}>
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Describe a layout change or a product to add…"
          disabled={isBusy}
          className="flex-1 rounded-lg border px-3 py-2 text-sm focus:ring-2 focus:ring-blue-600 outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isBusy || !draft.trim()}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  )
}
