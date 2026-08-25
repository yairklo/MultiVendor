'use client'

import React from 'react'
import Link from 'next/link'
import { motion, useReducedMotion } from 'motion/react'
import {
  Store, Users, Package, ShoppingCart, Wallet, Globe, LayoutTemplate, ArrowRight, CreditCard,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { SuperAdminPageHeader } from './SuperAdminPageHeader'
import { formatDate, formatPlatformMoney, type PlatformOverview } from './types'
import { orderStatusClass, orderStatusLabel } from '@/lib/orderStatus'

const kpiContainerVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05 } },
}

const kpiCardVariants = {
  hidden: { opacity: 0, y: 16 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] as const },
  },
}

function tenantBadge(status: string) {
  if (status === 'active') return 'success' as const
  if (status === 'suspended') return 'destructive' as const
  return 'warning' as const
}

export function OverviewClient({ overview }: { overview: PlatformOverview }) {
  const prefersReducedMotion = useReducedMotion()
  const kpis = [
    { label: 'Active stores', value: overview.tenants_active.toLocaleString(), hint: `${overview.tenants_total} total`, icon: Store, tone: 'text-primary' },
    { label: 'Platform GMV', value: formatPlatformMoney(overview.gmv), hint: `${overview.orders_total} orders`, icon: ShoppingCart, tone: 'text-emerald-500' },
    { label: 'Commission', value: formatPlatformMoney(overview.platform_commission), hint: 'Marketplace split', icon: CreditCard, tone: 'text-amber-500' },
    { label: 'Catalog products', value: overview.products_total.toLocaleString(), hint: `${overview.users_total} users`, icon: Package, tone: 'text-sky-500' },
    { label: 'Stripe Connect', value: overview.stripe_connected.toLocaleString(), hint: 'Vendors ready to payout', icon: Wallet, tone: 'text-violet-500' },
    { label: 'Marketplace', value: overview.marketplace_vendors.toLocaleString(), hint: 'Stores opted in', icon: Globe, tone: 'text-teal-500' },
    { label: 'Templates', value: overview.templates_active.toLocaleString(), hint: 'Live in seller catalog', icon: LayoutTemplate, tone: 'text-rose-500' },
    { label: 'Suspended', value: overview.tenants_suspended.toLocaleString(), hint: `${overview.tenants_cancelled} cancelled`, icon: Users, tone: 'text-destructive' },
  ]

  const shortcuts = [
    { href: '/super-admin/tenants', label: 'Onboard a store', hint: 'Create, suspend, change plans' },
    { href: '/super-admin/templates', label: 'Storefront templates', hint: 'Ship a new design without a deploy' },
    { href: '/super-admin/payouts', label: 'Review Connect', hint: 'Who can receive payouts' },
    { href: '/super-admin/audit', label: 'Audit trail', hint: 'Every platform action' },
  ]

  return (
    <div className="space-y-8">
      <SuperAdminPageHeader
        title="Platform overview"
        description="Health of every vendor store, payout, and marketplace listing on this installation."
      />

      <motion.div
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
        variants={prefersReducedMotion ? undefined : kpiContainerVariants}
        initial={prefersReducedMotion ? undefined : 'hidden'}
        animate={prefersReducedMotion ? undefined : 'show'}
      >
        {kpis.map((kpi) => {
          const Icon = kpi.icon
          return (
            <motion.div key={kpi.label} variants={prefersReducedMotion ? undefined : kpiCardVariants}>
              <Card className="shadow-sm transition-shadow duration-150 hover:shadow-md">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">{kpi.label}</CardTitle>
                  <Icon className={`h-4 w-4 ${kpi.tone}`} />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-foreground">{kpi.value}</div>
                  <p className="mt-1 text-xs text-muted-foreground">{kpi.hint}</p>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </motion.div>

      <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent stores</CardTitle>
            <Link
              href="/super-admin/tenants"
              className="inline-flex items-center gap-1 text-sm font-medium text-primary transition-colors duration-150 hover:text-primary/80"
            >
              All tenants <ArrowRight className="h-4 w-4" />
            </Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {overview.recent_tenants.length === 0 && (
              <p className="py-8 text-center text-sm text-muted-foreground">No tenants onboarded yet.</p>
            )}
            {overview.recent_tenants.map((tenant) => (
              <div key={tenant.id} className="flex items-center justify-between rounded-lg border border-border/60 px-3 py-2.5">
                <div>
                  <div className="font-semibold">{tenant.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {tenant.slug} · {tenant.plan_name} · {formatDate(tenant.created_at)}
                  </div>
                </div>
                <Badge variant={tenantBadge(tenant.status)}>{tenant.status}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Shortcuts</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            {shortcuts.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="group rounded-lg border border-border/60 px-3 py-3 transition-all duration-150 hover:border-primary/40 hover:bg-muted/40 active:scale-[0.99]"
              >
                <div className="flex items-center justify-between font-medium">
                  {item.label}
                  <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-primary" />
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">{item.hint}</p>
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card className="gap-0 py-0 shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between px-5 pt-5 pb-4">
          <CardTitle>Latest orders</CardTitle>
          <Link
            href="/super-admin/orders"
            className="inline-flex items-center gap-1 text-sm font-medium text-primary transition-colors duration-150 hover:text-primary/80"
          >
            All orders <ArrowRight className="h-4 w-4" />
          </Link>
        </CardHeader>
        {overview.recent_orders.length === 0 ? (
          <p className="px-5 pb-8 text-center text-sm text-muted-foreground">No orders across the platform yet.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Order</TableHead>
                <TableHead>Store</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-end">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {overview.recent_orders.map((order) => (
                <TableRow key={order.id}>
                  <TableCell className="font-medium">{order.order_number}</TableCell>
                  <TableCell className="text-muted-foreground">{order.tenant_name}</TableCell>
                  <TableCell>
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${orderStatusClass[order.status] || ''}`}>
                      {orderStatusLabel[order.status] || order.status}
                    </span>
                  </TableCell>
                  <TableCell className="text-end tabular-nums">{formatPlatformMoney(order.total_amount)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>
    </div>
  )
}
