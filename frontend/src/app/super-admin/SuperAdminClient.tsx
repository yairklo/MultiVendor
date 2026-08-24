'use client'

import React, { useState } from 'react'
import { apiClient } from '@/lib/api/apiClient'
import { useToast } from '@/context/ToastContext'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

export function SuperAdminClient({ initialTenants }: { initialTenants: any[] }) {
  const { showToast } = useToast()
  const [tenants, setTenants] = useState<any[]>(initialTenants)

  const fetchTenants = async () => {
    try {
      const response = await apiClient('/api/v1/super-admin/tenants')
      setTenants(response.data || [])
    } catch (e) {
      console.error(e)
    }
  }

  const toggleStatus = async (tenantId: string | number, currentStatus: string) => {
    const newStatus = currentStatus === 'active' ? 'suspended' : 'active'
    try {
      await apiClient(`/api/v1/super-admin/tenants/${tenantId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus })
      })
      fetchTenants()
      showToast(`Tenant ${newStatus === 'active' ? 'activated' : 'suspended'}`, 'success')
    } catch (e) {
      showToast('Failed to update status', 'error')
    }
  }

  return (
    <div className="p-8 bg-muted/30 min-h-screen text-foreground">
      <div className="mb-8">
        <h1 className="font-heading text-3xl font-bold tracking-tight text-foreground">Platform Super Admin</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage every tenant storefront running on the platform.</p>
      </div>

      <Card className="shadow-sm overflow-hidden py-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tenant Name & Domain</TableHead>
              <TableHead>Creation Date</TableHead>
              <TableHead>Products (Used / Max)</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tenants.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">No tenants registered yet.</TableCell>
              </TableRow>
            )}
            {tenants.map(tenant => (
              <TableRow key={tenant.id} className="hover:bg-muted/50 transition-colors">
                <TableCell>
                  <div className="font-bold">{tenant.name}</div>
                  <div className="text-sm text-muted-foreground">{tenant.slug}</div>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {new Date(tenant.created_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  {tenant.current_products_count || 0} / {tenant.max_products || '∞'}
                  <div className="text-xs text-muted-foreground">Tier: {tenant.subscription_tier}</div>
                </TableCell>
                <TableCell>
                  <Badge variant={tenant.status === 'active' ? 'success' : 'destructive'}>
                    {tenant.status.toUpperCase()}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => toggleStatus(tenant.id, tenant.status)}
                  >
                    {tenant.status === 'active' ? 'Suspend' : 'Activate'}
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
