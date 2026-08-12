'use client'

import React, { useState, useEffect } from 'react'
import { CatalogListing } from '@/components/storefront/CatalogListing'

export default function ShopPage(props: { params: Promise<{ tenant_slug: string }> | { tenant_slug: string } }) {
  const isPromise = props.params instanceof Promise
  const [tenantSlug, setTenantSlug] = useState<string | null>(isPromise ? null : (props.params as any).tenant_slug)

  useEffect(() => {
    if (isPromise) {
      ;(props.params as Promise<{ tenant_slug: string }>).then((p) => setTenantSlug(p.tenant_slug))
    }
  }, [props.params, isPromise])

  if (!tenantSlug) return <div>Loading...</div>

  return <CatalogListing tenantSlug={tenantSlug} />
}
