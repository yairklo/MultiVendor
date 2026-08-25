'use client'

import React from 'react'
import { CreditCard } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { SuperAdminPageHeader } from '../SuperAdminPageHeader'
import { formatPlatformMoney, type SubscriptionPlanAdmin } from '../types'

export function PlansClient({ plans }: { plans: SubscriptionPlanAdmin[] }) {
  return (
    <div className="space-y-6">
      <SuperAdminPageHeader
        title="Subscription plans"
        description="Tiers sellers subscribe to. Assign a plan from the Tenants page."
      />

      {plans.length === 0 ? (
        <Card className="py-16 text-center shadow-sm">
          <CreditCard className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">No plans configured.</p>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {plans.map((plan) => (
            <Card key={plan.id} className="shadow-sm transition-shadow duration-150 hover:shadow-md">
              <CardHeader className="flex flex-row items-start justify-between">
                <div>
                  <CardTitle className="text-xl">{plan.name}</CardTitle>
                  <p className="mt-1 font-mono text-xs text-muted-foreground">{plan.code}</p>
                </div>
                <Badge variant="secondary">{plan.tenant_count} stores</Badge>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="text-3xl font-bold">{formatPlatformMoney(plan.price_monthly)}</div>
                <p className="text-xs text-muted-foreground">per month</p>
                <ul className="space-y-1 text-sm text-muted-foreground">
                  <li>Up to {plan.max_products >= 999999 ? 'unlimited' : plan.max_products.toLocaleString()} products</li>
                  <li>{plan.max_storage_mb.toLocaleString()} MB storage</li>
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
