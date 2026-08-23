'use client'

import React, { useEffect, useRef, useState } from 'react'
import { Search } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api/apiClient'
import { ProductCard } from './ProductCard'
import { PageRenderer } from './PageRenderer'
import { PaginationControls, PaginationMeta } from '@/components/ui/pagination-controls'
import { ProductCardSkeleton } from '@/components/ui/skeleton'
import { useToast } from '@/context/ToastContext'
import { resolvePageKeyHref } from '@/lib/storefront-nav'
import { DispatchedAction, StorePageSchema } from '@/lib/ai/types'
import { useStorefrontTheme } from '@/context/StorefrontThemeContext'

const PAGE_SIZE = 12

type Lang = 'en' | 'he'

const strings: Record<Lang, { noProducts: string; switcherLabel: string; searchPlaceholder: string; allCategories: string }> = {
  en: { noProducts: 'No products found.', switcherLabel: 'עברית', searchPlaceholder: 'Search products...', allCategories: 'All Categories' },
  he: { noProducts: 'לא נמצאו מוצרים.', switcherLabel: 'English', searchPlaceholder: 'חיפוש מוצרים...', allCategories: 'כל הקטגוריות' },
}

/**
 * The full-featured catalog (search, category filter, pagination) — used both as the /shop
 * route every template's nav links to, and (via the optional aiPage props) as the home page's
 * fallback content. Deliberately not part of the AI-editable section-tree system: rearranging
 * search/filters/pagination via freeform sections would risk breaking real commerce
 * functionality for what's meant to be a decorative edit.
 */
export function CatalogListing({
  tenantSlug,
  aiPage,
  initialProducts,
  initialMeta,
  initialCategories,
}: {
  tenantSlug: string
  /** When set, shown instead of the classic grid while the shopper is just browsing (no active search/category filter). */
  aiPage?: StorePageSchema | null
  /** Server-fetched page-1/no-filter data, seeded in so first paint doesn't show a loading skeleton. */
  initialProducts?: any[]
  initialMeta?: PaginationMeta | null
  initialCategories?: any[]
}) {
  const router = useRouter()
  const { showToast } = useToast()
  const [products, setProducts] = useState<any[]>(initialProducts ?? [])
  const [productsLoading, setProductsLoading] = useState(!initialProducts)
  const [meta, setMeta] = useState<PaginationMeta | null>(initialMeta ?? null)
  const [page, setPage] = useState(1)
  const [categories, setCategories] = useState<any[]>(initialCategories ?? [])
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const { lang, setLang } = useStorefrontTheme()
  const t = strings[lang]

  function handleAiAction(action: DispatchedAction) {
    if (action.actionType === 'NAVIGATE') {
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

  // Searching or filtering by category always drops back to the classic full
  // catalog listing — the AI/template home page is a curated landing page, not a search UI.
  const isBrowsing = !debouncedSearch && !categoryId
  const showAiPage = isBrowsing && !!aiPage && aiPage.sections.length > 0

  useEffect(() => {
    const handle = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(handle)
  }, [search])

  const skipInitialCategoriesFetch = useRef(!!initialCategories)
  useEffect(() => {
    if (skipInitialCategoriesFetch.current) {
      skipInitialCategoriesFetch.current = false
      return
    }
    apiClient(`/api/v1/store/${tenantSlug}/categories`)
      .then(setCategories)
      .catch((e) => console.error('Failed to load categories:', e))
  }, [tenantSlug])

  useEffect(() => {
    setPage(1)
  }, [debouncedSearch, categoryId])

  const skipInitialProductsFetch = useRef(!!initialProducts)
  useEffect(() => {
    if (skipInitialProductsFetch.current) {
      skipInitialProductsFetch.current = false
      return
    }
    if (showAiPage) return
    setProductsLoading(true)
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) })
    if (debouncedSearch) params.set('q', debouncedSearch)
    if (categoryId) params.set('category_id', categoryId)
    apiClient(`/api/v1/store/${tenantSlug}/products?${params.toString()}`)
      .then((data) => {
        setProducts(data.data || [])
        setMeta(data.meta || null)
      })
      .catch((e) => {
        console.error('Failed to load products:', e)
        setProducts([])
        setMeta(null)
      })
      .finally(() => setProductsLoading(false))
  }, [tenantSlug, debouncedSearch, categoryId, page, showAiPage])

  return (
    <div
      dir={lang === 'he' ? 'rtl' : 'ltr'}
      className="min-h-full"
      style={
        showAiPage
          ? { backgroundColor: aiPage?.background_color || undefined, color: aiPage?.text_color || undefined }
          : undefined
      }
    >
    <div className="mx-auto max-w-6xl px-4 py-8 md:px-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-1 min-w-[240px] flex-wrap items-center gap-3">
          <div className="relative max-w-sm flex-1">
            <Search className="absolute left-3 top-1/2 w-4 h-4 -translate-y-1/2 text-gray-400" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t.searchPlaceholder}
              aria-label="Search products"
              className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-9 pr-3 outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>
          {categories.length > 0 && (
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              aria-label="Filter by category"
              className="rounded-lg border border-gray-200 bg-white px-3 py-2 outline-none focus:ring-2 focus:ring-blue-600"
            >
              <option value="">{t.allCategories}</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {typeof c.name === 'object' ? c.name?.[lang] || c.name?.en || c.name?.he : c.name}
                </option>
              ))}
            </select>
          )}
        </div>
        <button
          data-testid="language-switcher"
          className="cursor-pointer font-medium text-gray-600 transition-colors hover:text-blue-600"
          onClick={() => setLang(lang === 'en' ? 'he' : 'en')}
        >
          {t.switcherLabel}
        </button>
      </div>

      {showAiPage ? (
        <PageRenderer page={aiPage!} tenantSlug={tenantSlug} onAction={handleAiAction} />
      ) : (
        <>
          <div data-testid="product-grid" className="grid grid-cols-1 gap-6 md:grid-cols-3 lg:grid-cols-4">
            {productsLoading
              ? Array.from({ length: 8 }, (_, i) => <ProductCardSkeleton key={i} />)
              : products.map((p) => <ProductCard key={p.id} product={p} tenantSlug={tenantSlug} lang={lang} />)}
            {!productsLoading && products.length === 0 && (
              <div className="col-span-full py-12 text-center text-gray-500">{t.noProducts}</div>
            )}
          </div>

          {meta && meta.total_pages > 1 && (
            <div className="mt-6 rounded-lg bg-white shadow-sm">
              <PaginationControls meta={meta} onPageChange={setPage} />
            </div>
          )}
        </>
      )}
    </div>
    </div>
  )
}
