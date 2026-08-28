'use client'

import React, { useEffect, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { apiClient } from '@/lib/api/apiClient'
import { MarketplaceProductCard } from './MarketplaceProductCard'
import { PaginationControls, PaginationMeta } from '@/components/ui/pagination-controls'
import { ProductCardSkeleton } from '@/components/ui/skeleton'
import { useCurrency } from '@/hooks/useCurrency'
import { useUiLocale } from '@/context/UiLocaleContext'
import { isRtlLang } from '@/lib/languages'
import type { MarketplaceProduct } from '@/lib/types'

const PAGE_SIZE = 12

const gridContainerVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
}

const gridItemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] as const } },
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
  initialProducts?: MarketplaceProduct[]
  initialMeta?: PaginationMeta | null
}) {
  const { formatCurrency } = useCurrency()
  const { t, locale } = useUiLocale()
  const [products, setProducts] = useState<MarketplaceProduct[]>(initialProducts ?? [])
  const [productsLoading, setProductsLoading] = useState(!initialProducts)
  const [meta, setMeta] = useState<PaginationMeta | null>(initialMeta ?? null)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const prefersReducedMotion = useReducedMotion()

  useEffect(() => {
    const handle = setTimeout(() => {
      setDebouncedSearch(search)
      // Folded in here (rather than a separate effect keyed off
      // debouncedSearch) so resetting to page 1 on a new search isn't a
      // second synchronous setState-in-effect.
      setPage(1)
    }, 300)
    return () => clearTimeout(handle)
  }, [search])

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

  const showFeatured = !debouncedSearch && page === 1 && !productsLoading && products.length > 0
  const featured = showFeatured ? products[0] : null
  const rest = showFeatured ? products.slice(1) : products

  return (
    <div dir={isRtlLang(locale) ? 'rtl' : 'ltr'} className="min-h-full">
      <div className="mx-auto max-w-6xl px-4 pb-16 pt-10 md:px-8 md:pt-16">
        <header className="mb-12 border-b border-border pb-10 md:mb-16 md:pb-14">
          <p className="mb-4 text-[11px] font-medium uppercase tracking-[0.28em] text-muted-foreground">
            {t('marketplace.issue')}
          </p>
          <h1 className="max-w-3xl font-heading text-5xl font-medium leading-[1.05] text-foreground md:text-7xl">
            {t('marketplace.title')}
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground md:text-lg">
            {t('marketplace.manifesto')}
          </p>
          <label className="mt-10 block max-w-md">
            <span className="sr-only">{t('marketplace.searchAria')}</span>
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('marketplace.searchPlaceholder')}
              aria-label={t('marketplace.searchAria')}
              className="w-full border-0 border-b border-foreground/30 bg-transparent py-2 text-base outline-none transition-colors placeholder:text-muted-foreground/70 focus:border-foreground"
            />
          </label>
        </header>

        {featured && (
          <div className="mb-14">
            <MarketplaceProductCard
              product={featured}
              lang={locale}
              formatCurrency={formatCurrency}
              featured
            />
          </div>
        )}

        <motion.div
          data-testid="marketplace-product-grid"
          className="grid grid-cols-1 gap-x-8 gap-y-12 sm:grid-cols-2 lg:grid-cols-3"
          variants={prefersReducedMotion ? undefined : gridContainerVariants}
          initial={prefersReducedMotion ? undefined : 'hidden'}
          animate={prefersReducedMotion ? undefined : 'show'}
        >
          {productsLoading
            ? Array.from({ length: 6 }, (_, i) => <ProductCardSkeleton key={i} />)
            : rest.map((p) => (
                <motion.div key={p.id} variants={prefersReducedMotion ? undefined : gridItemVariants}>
                  <MarketplaceProductCard product={p} lang={locale} formatCurrency={formatCurrency} />
                </motion.div>
              ))}
          {!productsLoading && products.length === 0 && (
            <div className="col-span-full py-24 text-center">
              <p className="font-heading text-3xl text-foreground">{t('marketplace.noProducts')}</p>
            </div>
          )}
        </motion.div>

        {meta && meta.total_pages > 1 && (
          <div className="mt-14 border-t border-border pt-6">
            <PaginationControls meta={meta} onPageChange={setPage} />
          </div>
        )}
      </div>
    </div>
  )
}
