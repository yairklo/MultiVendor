'use client'

import React, { useEffect, useRef, useState } from 'react'
import { Search } from 'lucide-react'
import { apiClient } from '@/lib/api/apiClient'
import { MarketplaceProductCard } from './MarketplaceProductCard'
import { PaginationControls, PaginationMeta } from '@/components/ui/pagination-controls'
import { ProductCardSkeleton } from '@/components/ui/skeleton'
import { useCurrency } from '@/hooks/useCurrency'

const PAGE_SIZE = 12

type Lang = 'en' | 'he'

const strings: Record<Lang, { title: string; subtitle: string; noProducts: string; switcherLabel: string; searchPlaceholder: string }> = {
  en: {
    title: 'Marketplace',
    subtitle: 'Products from every store on the platform, in one place.',
    noProducts: 'No products found.',
    switcherLabel: 'עברית',
    searchPlaceholder: 'Search the marketplace...',
  },
  he: {
    title: 'שוק כללי',
    subtitle: 'מוצרים מכל החנויות בפלטפורמה, במקום אחד.',
    noProducts: 'לא נמצאו מוצרים.',
    switcherLabel: 'English',
    searchPlaceholder: 'חיפוש בשוק הכללי...',
  },
}

/**
 * Cross-store equivalent of storefront/CatalogListing. No category filter --
 * categories are per-tenant (see models/catalog.py Category.tenant_id) with no
 * shared taxonomy today, so there's nothing coherent to filter by here yet.
 */
export function MarketplaceListing({
  initialProducts,
  initialMeta,
}: {
  /** Server-fetched page-1/no-search data, seeded in so first paint doesn't show a loading skeleton. */
  initialProducts?: any[]
  initialMeta?: PaginationMeta | null
}) {
  const { formatCurrency } = useCurrency()
  const [products, setProducts] = useState<any[]>(initialProducts ?? [])
  const [productsLoading, setProductsLoading] = useState(!initialProducts)
  const [meta, setMeta] = useState<PaginationMeta | null>(initialMeta ?? null)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [lang, setLang] = useState<Lang>('en')
  const t = strings[lang]

  useEffect(() => {
    const handle = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(handle)
  }, [search])

  useEffect(() => {
    setPage(1)
  }, [debouncedSearch])

  const skipInitialFetch = useRef(!!initialProducts)
  useEffect(() => {
    if (skipInitialFetch.current) {
      skipInitialFetch.current = false
      return
    }
    setProductsLoading(true)
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) })
    if (debouncedSearch) params.set('q', debouncedSearch)
    apiClient(`/api/v1/marketplace/products?${params.toString()}`)
      .then((data) => {
        setProducts(data.data || [])
        setMeta(data.meta || null)
      })
      .catch((e) => {
        console.error('Failed to load marketplace products:', e)
        setProducts([])
        setMeta(null)
      })
      .finally(() => setProductsLoading(false))
  }, [debouncedSearch, page])

  return (
    <div dir={lang === 'he' ? 'rtl' : 'ltr'} className="min-h-full">
      <div className="mx-auto max-w-6xl px-4 py-8 md:px-8">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{t.title}</h1>
            <p className="mt-1 text-sm text-gray-500">{t.subtitle}</p>
          </div>
          <button
            data-testid="language-switcher"
            className="cursor-pointer font-medium text-gray-600 transition-colors hover:text-blue-600"
            onClick={() => setLang((l) => (l === 'en' ? 'he' : 'en'))}
          >
            {t.switcherLabel}
          </button>
        </div>

        <div className="relative mb-6 max-w-sm">
          <Search className="absolute left-3 top-1/2 w-4 h-4 -translate-y-1/2 text-gray-400" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t.searchPlaceholder}
            aria-label="Search marketplace"
            className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-9 pr-3 outline-none focus:ring-2 focus:ring-blue-600"
          />
        </div>

        <div data-testid="marketplace-product-grid" className="grid grid-cols-1 gap-6 md:grid-cols-3 lg:grid-cols-4">
          {productsLoading
            ? Array.from({ length: 8 }, (_, i) => <ProductCardSkeleton key={i} />)
            : products.map((p) => (
                <MarketplaceProductCard key={p.id} product={p} lang={lang} formatCurrency={formatCurrency} />
              ))}
          {!productsLoading && products.length === 0 && (
            <div className="col-span-full py-12 text-center text-gray-500">{t.noProducts}</div>
          )}
        </div>

        {meta && meta.total_pages > 1 && (
          <div className="mt-6 rounded-lg bg-white shadow-sm">
            <PaginationControls meta={meta} onPageChange={setPage} />
          </div>
        )}
      </div>
    </div>
  )
}
