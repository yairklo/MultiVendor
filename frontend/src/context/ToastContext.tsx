'use client'

import React, { createContext, useCallback, useContext, useState } from 'react'
import { CheckCircle2, XCircle, Info, X } from 'lucide-react'

export type ToastVariant = 'success' | 'error' | 'info'

interface ToastMessage {
  id: number
  message: string
  variant: ToastVariant
}

interface ToastContextValue {
  showToast: (message: string, variant?: ToastVariant) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const variantStyles: Record<ToastVariant, string> = {
  success: 'bg-green-600',
  error: 'bg-red-600',
  info: 'bg-gray-800',
}

const variantIcon: Record<ToastVariant, React.ReactNode> = {
  success: <CheckCircle2 className="w-5 h-5 shrink-0" />,
  error: <XCircle className="w-5 h-5 shrink-0" />,
  info: <Info className="w-5 h-5 shrink-0" />,
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const dismiss = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const showToast = useCallback((message: string, variant: ToastVariant = 'info') => {
    const id = Date.now() + Math.random()
    setToasts(prev => [...prev, { id, message, variant }])
    setTimeout(() => dismiss(id), 4000)
  }, [dismiss])

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 items-end pointer-events-none" aria-live="polite">
        {toasts.map(t => (
          <div
            key={t.id}
            role="status"
            data-testid="toast"
            className={`pointer-events-auto px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white flex items-center gap-2 min-w-[260px] max-w-sm animate-in slide-in-from-bottom-2 fade-in ${variantStyles[t.variant]}`}
          >
            {variantIcon[t.variant]}
            <span className="flex-1">{t.message}</span>
            <button onClick={() => dismiss(t.id)} aria-label="Dismiss notification" className="text-white/70 hover:text-white shrink-0">
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within a ToastProvider')
  return ctx
}
