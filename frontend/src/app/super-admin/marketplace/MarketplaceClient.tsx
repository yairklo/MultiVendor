'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { Globe } from 'lucide-react'
import { apiClient } from '@/lib/api/apiClient'
import { useToast } from '@/context/ToastContext'
import { errorMessage } from '@/lib/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { SuperAdminPageHeader } from '../SuperAdminPageHeader'
import type { TenantAdmin } from '../types'
import { isUsableTenantSlug } from '@/lib/tenantSlug'

export function MarketplaceClient({ initialTenants }: { initialTenants: TenantAdmin[] }) {
  const { showToast } = useToast()
  const [tenants, setTenants] = useState(initialTenants)
  const [busyId, setBusyId] = useState<number | null>(null)
  const listed = tenants.filter((t) => t.show_all_products_in_marketplace)

  async function reload() {
    const response = await apiClient('/api/v1/super-admin/tenants')
    setTenants(response.data || [])
  }

  async function toggle(tenant: TenantAdmin) {
    setBusyId(tenant.id)
    try {
      await apiClient(`/api/v1/super-admin/tenants/${tenant.id}/marketplace`, {
        method: 'PATCH',
        body: JSON.stringify({ show_all_products_in_marketplace: !tenant.show_all_products_in_marketplace }),
      })
      await reload()
      showToast('Marketplace listing updated', 'success')
    } catch (err) {
      showToast(errorMessage(err) || 'Failed to update marketplace', 'error')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="space-y-6">
      <SuperAdminPageHeader
        title="Marketplace"
        description={`${listed.length} stores currently list their catalog on the cross-vendor marketplace.`}
      />
      <Card className="overflow-hidden py-0 shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Store</TableHead>
              <TableHead>Products</TableHead>
              <TableHead>Listing</TableHead>
              <TableHead className="text-end">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tenants.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="py-12 text-center text-muted-foreground">
                  <Globe className="mx-auto mb-2 h-8 w-8 opacity-40" />
                  No stores yet.
                </TableCell>
              </TableRow>
            )}
            {tenants.map((tenant) => (
              <TableRow key={tenant.id} className="hover:bg-muted/50">
                <TableCell>
                  <div className="font-semibold">{tenant.name}</div>
                  {isUsableTenantSlug(tenant.slug) ? (
                    <Link href={`/store/${tenant.slug}`} prefetch={false} className="text-sm text-muted-foreground hover:text-primary">
                      {tenant.slug}
                    </Link>
                  ) : (
                    <span className="text-sm text-muted-foreground">{tenant.slug || '—'}</span>
                  )}
                </TableCell>
                <TableCell>{tenant.product_count}</TableCell>
                <TableCell>
                  <Badge variant={tenant.show_all_products_in_marketplace ? 'success' : 'outline'}>
                    {tenant.show_all_products_in_marketplace ? 'On marketplace' : 'Store only'}
                  </Badge>
                </TableCell>
                <TableCell className="text-end whitespace-nowrap">
                  <Button
                    variant={tenant.show_all_products_in_marketplace ? 'outline' : 'default'}
                    size="sm"
                    disabled={busyId === tenant.id}
                    onClick={() => toggle(tenant)}
                  >
                    {tenant.show_all_products_in_marketplace ? 'Remove' : 'List store'}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
