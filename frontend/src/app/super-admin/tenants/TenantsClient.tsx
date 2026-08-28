'use client'

import React, { useMemo, useState } from 'react'
import Link from 'next/link'
import { ExternalLink, Plus, Search, Store } from 'lucide-react'
import { apiClient } from '@/lib/api/apiClient'
import { useToast } from '@/context/ToastContext'
import { useConfirm } from '@/context/ConfirmContext'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { SuperAdminPageHeader } from '../SuperAdminPageHeader'
import {
  formatDate, nativeSelectClass, type SubscriptionPlanAdmin, type TenantAdmin,
} from '../types'
import { isUsableTenantSlug } from '@/lib/tenantSlug'
import { errorMessage } from '@/lib/errors'

function statusVariant(status: string) {
  if (status === 'active') return 'success' as const
  if (status === 'suspended') return 'destructive' as const
  return 'warning' as const
}

const EMPTY_FORM = {
  name: '',
  slug: '',
  plan_id: '',
  admin_email: '',
  admin_full_name: '',
  admin_password: '',
  show_all_products_in_marketplace: false,
}

export function TenantsClient({
  initialTenants,
  plans,
}: {
  initialTenants: TenantAdmin[]
  plans: SubscriptionPlanAdmin[]
}) {
  const { showToast } = useToast()
  const { confirm } = useConfirm()
  const [tenants, setTenants] = useState(initialTenants)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [busyId, setBusyId] = useState<number | null>(null)
  const [creating, setCreating] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)

  async function reload() {
    const params = new URLSearchParams()
    if (statusFilter !== 'all') params.set('status', statusFilter)
    if (query.trim()) params.set('q', query.trim())
    const qs = params.toString()
    const response = await apiClient(`/api/v1/super-admin/tenants${qs ? `?${qs}` : ''}`)
    setTenants(response.data || [])
  }

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    return tenants.filter((tenant) => {
      if (statusFilter !== 'all' && tenant.status !== statusFilter) return false
      if (!q) return true
      return (
        tenant.name.toLowerCase().includes(q)
        || tenant.slug.toLowerCase().includes(q)
        || (tenant.custom_domain || '').toLowerCase().includes(q)
      )
    })
  }, [tenants, query, statusFilter])

  async function toggleStatus(tenant: TenantAdmin) {
    const next = tenant.status === 'active' ? 'suspended' : 'active'
    if (next === 'suspended') {
      const ok = await confirm({
        title: `Suspend ${tenant.name}?`,
        description: 'The store and its storefront will stop accepting orders until it is reactivated.',
        confirmLabel: 'Suspend store',
        cancelLabel: 'Cancel',
        variant: 'destructive',
      })
      if (!ok) return
    }
    setBusyId(tenant.id)
    try {
      await apiClient(`/api/v1/super-admin/tenants/${tenant.id}/status?status=${next}`, { method: 'PATCH' })
      await reload()
      showToast(next === 'active' ? 'Store activated' : 'Store suspended', 'success')
    } catch (err) {
      showToast(errorMessage(err) || 'Failed to update status', 'error')
    } finally {
      setBusyId(null)
    }
  }

  async function changePlan(tenant: TenantAdmin, planId: number) {
    if (planId === tenant.plan_id) return
    setBusyId(tenant.id)
    try {
      await apiClient(`/api/v1/super-admin/tenants/${tenant.id}/subscription`, {
        method: 'POST',
        body: JSON.stringify({ plan_id: planId }),
      })
      await reload()
      showToast('Plan updated', 'success')
    } catch (err) {
      showToast(errorMessage(err) || 'Failed to change plan', 'error')
    } finally {
      setBusyId(null)
    }
  }

  async function toggleMarketplace(tenant: TenantAdmin) {
    setBusyId(tenant.id)
    try {
      await apiClient(`/api/v1/super-admin/tenants/${tenant.id}/marketplace`, {
        method: 'PATCH',
        body: JSON.stringify({ show_all_products_in_marketplace: !tenant.show_all_products_in_marketplace }),
      })
      await reload()
      showToast(
        tenant.show_all_products_in_marketplace ? 'Removed from marketplace' : 'Added to marketplace',
        'success',
      )
    } catch (err) {
      showToast(errorMessage(err) || 'Failed to update marketplace', 'error')
    } finally {
      setBusyId(null)
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setCreating(true)
    try {
      await apiClient('/api/v1/super-admin/tenants', {
        method: 'POST',
        body: JSON.stringify({
          name: form.name.trim(),
          slug: form.slug.trim(),
          plan_id: Number(form.plan_id || plans[0]?.id),
          admin_email: form.admin_email.trim(),
          admin_full_name: form.admin_full_name.trim(),
          admin_password: form.admin_password,
          show_all_products_in_marketplace: form.show_all_products_in_marketplace,
        }),
      })
      showToast('Store created', 'success')
      setForm(EMPTY_FORM)
      setShowCreate(false)
      await reload()
    } catch (err) {
      showToast(errorMessage(err) || 'Failed to create store', 'error')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-6">
      <SuperAdminPageHeader
        title="Tenants"
        description="Every vendor store on the platform — plans, marketplace listing, and suspension."
        actions={
          <Button type="button" onClick={() => setShowCreate((v) => !v)}>
            <Plus className="h-4 w-4" />
            New store
          </Button>
        }
      />

      {showCreate && (
        <Card className="p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-bold">Onboard a store</h2>
          <form onSubmit={handleCreate} className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="tenant_name">Store name</Label>
              <Input id="tenant_name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required minLength={3} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="tenant_slug">Slug</Label>
              <Input id="tenant_slug" value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} required pattern="[a-z0-9-]+" placeholder="acme-shop" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="tenant_plan">Plan</Label>
              <select
                id="tenant_plan"
                className={`w-full ${nativeSelectClass}`}
                value={form.plan_id}
                onChange={(e) => setForm({ ...form, plan_id: e.target.value })}
                required
              >
                <option value="">Select a plan</option>
                {plans.map((plan) => (
                  <option key={plan.id} value={plan.id}>{plan.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="admin_full_name">Owner name</Label>
              <Input id="admin_full_name" value={form.admin_full_name} onChange={(e) => setForm({ ...form, admin_full_name: e.target.value })} required />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="admin_email">Owner email</Label>
              <Input id="admin_email" type="email" value={form.admin_email} onChange={(e) => setForm({ ...form, admin_email: e.target.value })} required />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="admin_password">Owner password</Label>
              <Input id="admin_password" type="password" value={form.admin_password} onChange={(e) => setForm({ ...form, admin_password: e.target.value })} required minLength={8} />
            </div>
            <label className="flex items-center gap-2 text-sm md:col-span-2">
              <input
                type="checkbox"
                checked={form.show_all_products_in_marketplace}
                onChange={(e) => setForm({ ...form, show_all_products_in_marketplace: e.target.checked })}
              />
              List this store on the marketplace
            </label>
            <div className="flex justify-end gap-2 md:col-span-2">
              <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
              <Button type="submit" disabled={creating}>{creating ? 'Creating…' : 'Create store'}</Button>
            </div>
          </form>
        </Card>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search name or slug"
            className="pl-9"
          />
        </div>
        <select
          className={nativeSelectClass}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="all">All statuses</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      <Card className="overflow-hidden py-0 shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Store</TableHead>
              <TableHead>Plan</TableHead>
              <TableHead>Products</TableHead>
              <TableHead>Marketplace</TableHead>
              <TableHead>Payouts</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-end">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visible.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="py-12 text-center text-muted-foreground">
                  <Store className="mx-auto mb-2 h-8 w-8 opacity-40" />
                  No tenants match this filter.
                </TableCell>
              </TableRow>
            )}
            {visible.map((tenant) => (
              <TableRow key={tenant.id} className="hover:bg-muted/50">
                <TableCell>
                  <div className="font-bold">{tenant.name}</div>
                  <div className="text-sm text-muted-foreground">
                    {tenant.slug}
                    {tenant.custom_domain ? ` · ${tenant.custom_domain}` : ''}
                    {' · '}
                    {formatDate(tenant.created_at)}
                  </div>
                </TableCell>
                <TableCell>
                  <select
                    className={nativeSelectClass}
                    value={tenant.plan_id}
                    disabled={busyId === tenant.id}
                    onChange={(e) => changePlan(tenant, Number(e.target.value))}
                  >
                    {plans.map((plan) => (
                      <option key={plan.id} value={plan.id}>{plan.name}</option>
                    ))}
                  </select>
                </TableCell>
                <TableCell>
                  {tenant.product_count} / {tenant.max_products >= 999999 ? '∞' : tenant.max_products}
                </TableCell>
                <TableCell>
                  <Button
                    variant={tenant.show_all_products_in_marketplace ? 'secondary' : 'outline'}
                    size="sm"
                    disabled={busyId === tenant.id}
                    onClick={() => toggleMarketplace(tenant)}
                  >
                    {tenant.show_all_products_in_marketplace ? 'Listed' : 'Off'}
                  </Button>
                </TableCell>
                <TableCell>
                  <Badge variant={tenant.stripe_connected ? 'success' : 'outline'}>
                    {tenant.stripe_connected ? 'Connected' : 'Not connected'}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={statusVariant(tenant.status)}>{tenant.status}</Badge>
                </TableCell>
                <TableCell className="text-end">
                  <div className="flex justify-end gap-2">
                    {isUsableTenantSlug(tenant.slug) && (
                    <Link
                      href={`/store/${tenant.slug}`}
                      target="_blank"
                      prefetch={false}
                      className="inline-flex h-7 items-center gap-1 rounded-[min(var(--radius-md),12px)] border border-border bg-background px-2.5 text-[0.8rem] font-medium transition-all duration-150 hover:bg-muted active:scale-[0.98]"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      Store
                    </Link>
                    )}
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={busyId === tenant.id}
                      onClick={() => toggleStatus(tenant)}
                    >
                      {tenant.status === 'active' ? 'Suspend' : 'Activate'}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
