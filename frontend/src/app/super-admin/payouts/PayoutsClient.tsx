'use client'

import React from 'react'
import Link from 'next/link'
import { Wallet } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { SuperAdminPageHeader } from '../SuperAdminPageHeader'
import type { TenantAdmin } from '../types'
import { isUsableTenantSlug } from '@/lib/tenantSlug'

export function PayoutsClient({ tenants }: { tenants: TenantAdmin[] }) {
  const connected = tenants.filter((t) => t.stripe_connected).length

  return (
    <div className="space-y-6">
      <SuperAdminPageHeader
        title="Payouts & Connect"
        description={`${connected} of ${tenants.length} stores have a Stripe Connect account. Sellers complete onboarding from their own admin.`}
      />
      <Card className="overflow-hidden py-0 shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Store</TableHead>
              <TableHead>Plan</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Connect</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tenants.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="py-12 text-center text-muted-foreground">
                  <Wallet className="mx-auto mb-2 h-8 w-8 opacity-40" />
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
                <TableCell>{tenant.plan_name}</TableCell>
                <TableCell>
                  <Badge variant={tenant.status === 'active' ? 'success' : 'destructive'}>{tenant.status}</Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={tenant.stripe_connected ? 'success' : 'outline'}>
                    {tenant.stripe_connected ? 'Connected' : 'Not connected'}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
