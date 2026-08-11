'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { apiClient, ApiError } from '@/lib/api/apiClient'
import { useToast } from '@/context/ToastContext'
import { PageRenderer } from '@/components/storefront/PageRenderer'
import { DispatchedAction, StorePageSchema } from '@/lib/ai/types'

export default function StorefrontDynamicPage(props: {
  params: Promise<{ tenant_slug: string; page_key: string }> | { tenant_slug: string; page_key: string }
}) {
  const isPromise = props.params instanceof Promise
  const [params, setParams] = useState<{ tenant_slug: string; page_key: string } | null>(
    isPromise ? null : (props.params as any)
  )

  useEffect(() => {
    if (isPromise) {
      ;(props.params as Promise<{ tenant_slug: string; page_key: string }>).then(setParams)
    }
  }, [props.params, isPromise])

  const router = useRouter()
  const { showToast } = useToast()
  const [page, setPage] = useState<StorePageSchema | null>(null)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (!params) return
    setPage(null)
    setNotFound(false)
    apiClient(`/api/v1/store/${params.tenant_slug}/pages/${params.page_key}`)
      .then(setPage)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          setNotFound(true)
        } else {
          showToast(err.message || 'Failed to load page', 'error')
        }
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params?.tenant_slug, params?.page_key])

  function handleAction(action: DispatchedAction) {
    if (action.actionType === 'NAVIGATE' && params) {
      // Prefer page_key (an AI-authored button linking to another page on this
      // store) — the AI is never told this store's tenant_slug/URL structure,
      // so it can only reference other pages by key, never by a guessed href.
      if (typeof action.actionPayload?.page_key === 'string') {
        router.push(`/store/${params.tenant_slug}/pages/${action.actionPayload.page_key}`)
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

  if (!params) return <div className="min-h-screen bg-gray-50" />

  if (notFound) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-gray-50 text-center">
        <h1 className="text-xl font-bold text-gray-900">Page not found</h1>
        <p className="text-gray-500">This store has no page called &ldquo;{params.page_key}&rdquo;.</p>
        <Link href={`/store/${params.tenant_slug}`} className="font-medium text-blue-600 hover:underline">
          Back to store
        </Link>
      </div>
    )
  }

  return (
    <div
      className="min-h-screen bg-gray-50 px-4 py-8 md:px-8"
      style={{ backgroundColor: page?.background_color || undefined, color: page?.text_color || undefined }}
    >
      <div className="mx-auto max-w-5xl">
        <PageRenderer page={page} tenantSlug={params.tenant_slug} onAction={handleAction} />
      </div>
    </div>
  )
}
