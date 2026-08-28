'use client'

import React from 'react'
import Link from 'next/link'
import { motion, useReducedMotion } from 'motion/react'
import { orderStatusClass, orderStatusLabel } from '@/lib/orderStatus'
import { stockLevel, stockLevelClass } from '@/lib/stock'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Package, Star, ArrowRight } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useCurrency } from '@/hooks/useCurrency'
import { useUiLocale } from '@/context/UiLocaleContext'
import { formatUiChartDay, formatUiDate } from '@/lib/utils'
import type { Order, Product, ProductReview } from '@/lib/types'

interface DashboardMetrics {
  data: { date?: string | null; total_sales: number; order_count: number }[]
  total_revenue: number
  orders_count: number
  aov: number
}

interface TopProduct {
  sku: string
  product_name: string
  quantity_sold: number
  revenue: number
}

type LowStockProduct = Product & { _stock: number }

const kpiContainerVariants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.05 },
  },
}

const kpiCardVariants = {
  hidden: { opacity: 0, y: 16 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] as const },
  },
}

export function DashboardClient({
  metrics,
  topProducts,
  recentOrders,
  lowStockProducts,
  recentReviews,
}: {
  metrics: DashboardMetrics | null
  topProducts: TopProduct[]
  recentOrders: Order[]
  lowStockProducts: LowStockProduct[]
  recentReviews: ProductReview[]
}) {
  const { formatCurrency } = useCurrency()
  const { t, locale } = useUiLocale()
  const prefersReducedMotion = useReducedMotion()
  const chartData = metrics?.data?.map((d) => ({
    date: formatUiChartDay(d.date, locale),
    Revenue: d.total_sales,
    Orders: d.order_count
  })) || []

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-heading text-4xl font-medium tracking-tight text-foreground">{t('dashboard.title')}</h1>
          <p className="mt-2 text-sm text-muted-foreground">{t('dashboard.subtitle')}</p>
        </div>
        <Badge variant="outline" className="rounded-none px-3 py-1 text-[11px] uppercase tracking-[0.16em]">{t('dashboard.last30')}</Badge>
      </div>

      {/* KPI strip — typographic, not icon cards */}
      <motion.div
        className="grid grid-cols-1 divide-y divide-border border-y border-border md:grid-cols-4 md:divide-x md:divide-y-0"
        variants={prefersReducedMotion ? undefined : kpiContainerVariants}
        initial={prefersReducedMotion ? undefined : 'hidden'}
        animate={prefersReducedMotion ? undefined : 'show'}
      >
        <motion.div variants={prefersReducedMotion ? undefined : kpiCardVariants} className="px-0 py-6 md:px-6 md:py-8 first:ps-0">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">{t('dashboard.totalRevenue')}</p>
          <p className="mt-3 font-heading text-3xl tabular-nums text-foreground md:text-4xl">{formatCurrency(metrics?.total_revenue || 0)}</p>
          <p className="mt-2 text-xs text-muted-foreground">+20.1% {t('dashboard.fromLastMonth')}</p>
        </motion.div>

        <motion.div variants={prefersReducedMotion ? undefined : kpiCardVariants} className="px-0 py-6 md:px-6 md:py-8">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">{t('dashboard.totalOrders')}</p>
          <p className="mt-3 font-heading text-3xl tabular-nums text-foreground md:text-4xl">{(metrics?.orders_count || 0).toLocaleString()}</p>
          <p className="mt-2 text-xs text-muted-foreground">+12.5% {t('dashboard.fromLastMonth')}</p>
        </motion.div>

        <motion.div variants={prefersReducedMotion ? undefined : kpiCardVariants} className="px-0 py-6 md:px-6 md:py-8">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">{t('dashboard.aov')}</p>
          <p className="mt-3 font-heading text-3xl tabular-nums text-foreground md:text-4xl">{formatCurrency(metrics?.aov || 0)}</p>
          <p className="mt-2 text-xs text-muted-foreground">{t('dashboard.basedOnPaid')}</p>
        </motion.div>

        <motion.div variants={prefersReducedMotion ? undefined : kpiCardVariants} className="px-0 py-6 md:px-6 md:py-8 last:pe-0">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">{t('dashboard.activeProducts')}</p>
          <p className="mt-3 font-heading text-3xl tabular-nums text-foreground md:text-4xl">{topProducts.length * 12 || 45}</p>
          <p className="mt-2 text-xs text-muted-foreground">{t('dashboard.itemsLowStock', { count: lowStockProducts.length })}</p>
        </motion.div>
      </motion.div>

      {/* Main Charts & Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-7 gap-6">
        <Card className="lg:col-span-4 shadow-sm">
          <CardHeader>
            <CardTitle>{t('dashboard.revenueOverview')}</CardTitle>
            <CardDescription>{t('dashboard.revenueOverviewDesc')}</CardDescription>
          </CardHeader>
          <CardContent className="px-2">
            <div className="h-[350px] w-full mt-4">
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                    <XAxis
                      dataKey="date"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }}
                      dy={10}
                    />
                    <YAxis
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }}
                      tickFormatter={(value) => formatCurrency(value)}
                    />
                    <Tooltip
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', background: 'var(--popover)', color: 'var(--popover-foreground)' }}
                      formatter={(value) => [formatCurrency(Number(value) || 0), t('dashboard.revenue')]}
                    />
                    <Area type="monotone" dataKey="Revenue" stroke="var(--chart-1)" strokeWidth={2} fillOpacity={1} fill="url(#colorRevenue)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
                  {t('dashboard.noChartData')}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-3 shadow-sm">
          <CardHeader>
            <CardTitle>{t('dashboard.topSelling')}</CardTitle>
            <CardDescription>{t('dashboard.topSellingDesc')}</CardDescription>
          </CardHeader>
          <CardContent>
            {topProducts.length === 0 ? (
              <p className="text-muted-foreground text-sm py-4 text-center">{t('dashboard.noSales')}</p>
            ) : (
              <div className="space-y-6">
                {topProducts.map((p, i) => (
                  <div key={i} className="flex items-center">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted border border-border">
                      <Package className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div className="ml-4 space-y-1 overflow-hidden">
                      <p className="text-sm font-medium leading-none truncate pr-4" title={p.product_name}>{p.product_name}</p>
                      <p className="text-sm text-muted-foreground">{t('dashboard.skuLine', { sku: p.sku || 'N/A', count: p.quantity_sold })}</p>
                    </div>
                    <div className="ml-auto font-medium text-emerald-600">
                      {formatCurrency(p.revenue)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Lists / Tabs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>{t('dashboard.recentOrders')}</CardTitle>
              <CardDescription>{t('dashboard.recentOrdersDesc')}</CardDescription>
            </div>
            <Link href="/admin/orders" className="text-sm text-primary hover:text-primary/80 flex items-center group transition-colors">
              {t('dashboard.viewAll')} <ArrowRight className="h-3 w-3 ml-1 group-hover:translate-x-1 transition-transform" />
            </Link>
          </CardHeader>
          <CardContent>
            {recentOrders.length === 0 ? (
              <p className="text-muted-foreground text-sm">{t('dashboard.noOrdersYet')}</p>
            ) : (
              <div className="space-y-5">
                {recentOrders.map(order => (
                  <div key={order.id} className="flex items-center">
                    <Avatar className="h-9 w-9">
                      <AvatarFallback className="bg-primary/10 text-primary text-xs font-medium">
                        {(order.customer_name || 'G')[0].toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="ml-4 space-y-1">
                      <p className="text-sm font-medium leading-none">{order.customer_name || t('orders.guest')}</p>
                      <p className="text-xs text-muted-foreground">{t('dashboard.orderHash', { id: order.id })} &middot; {formatUiDate(order.created_at, locale)}</p>
                    </div>
                    <div className="ml-auto flex items-center space-x-3">
                      <span className="text-sm font-medium">{formatCurrency(Number(order.total_amount))}</span>
                      <Badge variant="outline" className={`${orderStatusClass[order.status] || ''} capitalize whitespace-nowrap rounded-md font-medium px-2 py-0.5`}>
                        {orderStatusLabel[order.status] ? t(`orderStatus.${order.status}`) : order.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <Tabs defaultValue="lowstock" className="w-full">
            <CardHeader className="pb-3 border-b border-border">
              <div className="flex items-center justify-between">
                <TabsList className="bg-muted/50">
                  <TabsTrigger value="lowstock">{t('dashboard.lowStock')}</TabsTrigger>
                  <TabsTrigger value="reviews">{t('dashboard.recentReviews')}</TabsTrigger>
                </TabsList>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <TabsContent value="lowstock" className="mt-0">
                {lowStockProducts.length === 0 ? (
                  <p className="text-muted-foreground text-sm py-4">{t('dashboard.inventoryHealthy')}</p>
                ) : (
                  <div className="space-y-4">
                    {lowStockProducts.map((p) => {
                      const level = stockLevel(p._stock)
                      return (
                        <div key={p.id} className="flex items-center justify-between border-b border-border pb-3 last:border-0 last:pb-0">
                          <div className="flex items-center">
                            <div className={`h-2 w-2 rounded-full mr-3 ${p._stock === 0 ? 'bg-red-500' : 'bg-orange-500'}`} />
                            <span className="text-sm font-medium text-foreground line-clamp-1 pr-4">
                              {typeof p.name === 'object' ? (p.name?.[locale] || p.name?.en || p.name?.he || t('products.unnamed')) : p.name}
                            </span>
                          </div>
                          <Badge variant="outline" className={`${stockLevelClass[level]} rounded-md px-2 py-0.5 whitespace-nowrap`}>
                            {t('dashboard.inStockCount', { count: p._stock })}
                          </Badge>
                        </div>
                      )
                    })}
                  </div>
                )}
              </TabsContent>
              <TabsContent value="reviews" className="mt-0">
                {recentReviews.length === 0 ? (
                  <p className="text-muted-foreground text-sm py-4">{t('reviews.none')}</p>
                ) : (
                  <div className="space-y-4">
                    {recentReviews.map((r) => (
                      <div key={r.id} className="flex items-start space-x-3 border-b border-border pb-3 last:border-0 last:pb-0">
                        <div className="flex bg-yellow-50 text-yellow-600 px-1.5 py-1 rounded-md text-xs font-bold items-center shrink-0">
                          {r.rating} <Star className="h-3 w-3 ml-0.5 fill-yellow-500 text-yellow-500" />
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">{r.comment}</p>
                          <p className="text-xs text-muted-foreground/70 mt-1">{t('reviews.by', { name: r.customer_name ?? t('orders.guest') })}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </TabsContent>
            </CardContent>
          </Tabs>
        </Card>
      </div>
    </div>
  )
}
