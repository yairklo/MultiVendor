'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient, ApiError } from '@/lib/api/apiClient'
import { useToast } from '@/context/ToastContext'
import { CatalogListing } from '@/components/storefront/CatalogListing'
import { resolvePageKeyHref } from '@/lib/storefront-nav'
import { DispatchedAction, StorePageSchema } from '@/lib/ai/types'

export default function StorefrontPage(props: { params: Promise<{ tenant_slug: string }> | { tenant_slug: string } }) {
  // Handle both promise and plain object for testing flexibility
  const isPromise = props.params instanceof Promise
  const [tenantSlug, setTenantSlug] = useState<string | null>(isPromise ? null : (props.params as any).tenant_slug)

  useEffect(() => {
    if (isPromise) {
      ;(props.params as Promise<{ tenant_slug: string }>).then(p => setTenantSlug(p.tenant_slug))
    }
  }, [props.params, isPromise])

  const router = useRouter()
  const { showToast } = useToast()

  // The vendor's AI/CMS-managed "home" layout, if they've used the AI Layout
  // editor (or applied a premium template) — CatalogListing falls back to the
  // classic catalog listing when there is none yet (aiPage stays null), so
  // untouched stores are unaffected.
  const [aiPage, setAiPage] = useState<StorePageSchema | null>(null)

  useEffect(() => {
    if (!tenantSlug) return
    apiClient(`/api/v1/store/${tenantSlug}/pages/home`)
      .then((data) => setAiPage(data))
      .catch((e) => {
        if (!(e instanceof ApiError && e.status === 404)) console.error('Failed to load AI home layout:', e)
        setAiPage(null)
      })
  }, [tenantSlug])

  function handleAiHomeAction(action: DispatchedAction) {
    if (action.actionType === 'NAVIGATE' && tenantSlug) {
      // Prefer page_key (an AI-authored button linking to another page on this
      // store) — the AI is never told this store's URL structure, so it can
      // only reference other pages by key, never by a guessed href.
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
      showToast(`${action.label}: pick a product below to add it to your cart.`, 'info')
      return
    }
    if (action.actionType === 'APPLY_COUPON') {
      showToast(`${action.label}: apply your coupon code at checkout.`, 'info')
      return
    }
    showToast(action.label, 'info')
  }

  if (!tenantSlug) return <div>Loading...</div>

  return <CatalogListing tenantSlug={tenantSlug} aiPage={aiPage} onAiAction={handleAiHomeAction} />
}
