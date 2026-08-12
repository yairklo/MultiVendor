'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import { useToast } from '@/context/ToastContext'
import { PageRenderer } from './PageRenderer'
import { resolvePageKeyHref } from '@/lib/storefront-nav'
import { DispatchedAction, StorePageSchema } from '@/lib/ai/types'

export function DynamicPageView({ page, tenantSlug }: { page: StorePageSchema; tenantSlug: string }) {
  const router = useRouter()
  const { showToast } = useToast()

  function handleAction(action: DispatchedAction) {
    if (action.actionType === 'NAVIGATE') {
      // Prefer page_key (an AI-authored button linking to another page on this
      // store) — the AI is never told this store's tenant_slug/URL structure,
      // so it can only reference other pages by key, never by a guessed href.
      if (typeof action.actionPayload?.page_key === 'string') {
        router.push(resolvePageKeyHref(tenantSlug, action.actionPayload.page_key))
        return
      }
      if (typeof action.actionPayload?.href === 'string') {
        router.push(action.actionPayload.href)
        return
      }
    }
    if (action.actionType === 'ADD_TO_CART') {
      showToast(`${action.label}: add-to-cart isn't wired to a specific product from this page yet.`, 'info')
      return
    }
    if (action.actionType === 'APPLY_COUPON') {
      showToast(`${action.label}: visit checkout to apply a coupon code.`, 'info')
      return
    }
    showToast(action.label, 'info')
  }

  return (
    <div
      className="min-h-screen bg-gray-50 px-4 py-8 md:px-8"
      style={{ backgroundColor: page.background_color || undefined, color: page.text_color || undefined }}
    >
      <div className="mx-auto max-w-5xl">
        <PageRenderer page={page} tenantSlug={tenantSlug} onAction={handleAction} />
      </div>
    </div>
  )
}
