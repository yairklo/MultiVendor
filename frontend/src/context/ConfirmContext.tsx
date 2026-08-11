'use client'

import React, { createContext, useCallback, useContext, useRef, useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

interface ConfirmOptions {
  title: string
  description?: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'default' | 'destructive'
}

interface ConfirmContextValue {
  confirm: (options: ConfirmOptions) => Promise<boolean>
}

const ConfirmContext = createContext<ConfirmContextValue | null>(null)

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const [options, setOptions] = useState<ConfirmOptions | null>(null)
  const resolverRef = useRef<((value: boolean) => void) | null>(null)

  const confirm = useCallback((opts: ConfirmOptions) => {
    setOptions(opts)
    setOpen(true)
    return new Promise<boolean>(resolve => {
      resolverRef.current = resolve
    })
  }, [])

  const settle = (result: boolean) => {
    setOpen(false)
    resolverRef.current?.(result)
    resolverRef.current = null
  }

  return (
    <ConfirmContext.Provider value={{ confirm }}>
      {children}
      <Dialog open={open} onOpenChange={(next: boolean) => { if (!next) settle(false) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{options?.title}</DialogTitle>
            {options?.description && <DialogDescription>{options.description}</DialogDescription>}
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => settle(false)}>
              {options?.cancelLabel || 'Cancel'}
            </Button>
            <Button
              variant={options?.variant === 'destructive' ? 'destructive' : 'default'}
              onClick={() => settle(true)}
            >
              {options?.confirmLabel || 'Confirm'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </ConfirmContext.Provider>
  )
}

export function useConfirm(): ConfirmContextValue {
  const ctx = useContext(ConfirmContext)
  if (!ctx) throw new Error('useConfirm must be used within a ConfirmProvider')
  return ctx
}
