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
import { DollarSign, ShoppingBag, Activity, TrendingUp, Package, Star, ArrowRight } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useCurrency } from '@/hooks/useCurrency'
import { useUiLocale } from '@/context/UiLocaleContext'
import { formatUiChartDay, formatUiDate } from '@/lib/utils'

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
  metrics: any
  topProducts: any[]
  recentOrders: any[]
  lowStockProducts: any[]
  recentReviews: any[]
}) {
  const { formatCurrency } = useCurrency()
  const { t, locale } = useUiLocale()
  const prefersReducedMotion = useReducedMotion()
  const chartData = metrics?.data?.map((d: any) => ({
    date: formatUiChartDay(d.date, locale),
    Revenue: d.total_sales,
    Orders: d.order_count
  })) || []

  return (
    <div className="p-8 bg-muted/30 min-h-screen space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="font-heading text-3xl font-bold tracking-tight text-foreground">{t('dashboard.title')}</h1>
          <p className="text-sm text-muted-foreground mt-1">{t('dashboard.subtitle')}</p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className="bg-card px-3 py-1">{t('dashboard.last30')}</Badge>
        </div>
      </div>

      {/* KPI Cards */}
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
        variants={prefersReducedMotion ? undefined : kpiContainerVariants}
        initial={prefersReducedMotion ? undefined : 'hidden'}
        animate={prefersReducedMotion ? undefined : 'show'}
      >
        <motion.div variants={prefersReducedMotion ? undefined : kpiCardVariants}>
          <Card className="shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{t('dashboard.totalRevenue')}</CardTitle>
              <DollarSign className="h-4 w-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-foreground">{formatCurrency(metrics?.total_revenue || 0)}</div>
              <p className="text-xs text-emerald-600 flex items-center mt-1 font-medium">
                <TrendingUp className="h-3 w-3 mr-1" /> +20.1% {t('dashboard.fromLastMonth')}
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={prefersReducedMotion ? undefined : kpiCardVariants}>
          <Card className="shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{t('dashboard.totalOrders')}</CardTitle>
              <ShoppingBag className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-foreground">{(metrics?.orders_count || 0).toLocaleString()}</div>
              <p className="text-xs text-primary flex items-center mt-1 font-medium">
                <TrendingUp className="h-3 w-3 mr-1" /> +12.5% {t('dashboard.fromLastMonth')}
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={prefersReducedMotion ? undefined : kpiCardVariants}>
          <Card className="shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{t('dashboard.aov')}</CardTitle>
              <Activity className="h-4 w-4 text-[oklch(0.62_0.19_300)]" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-foreground">{formatCurrency(metrics?.aov || 0)}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {t('dashboard.basedOnPaid')}
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={prefersReducedMotion ? undefined : kpiCardVariants}>
          <Card className="shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{t('dashboard.activeProducts')}</CardTitle>
              <Package className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-foreground">{topProducts.length * 12 || 45}</div>
              <p className="text-xs text-muted-foreground mt-1 flex items-center">
                {t('dashboard.itemsLowStock', { count: lowStockProducts.length })}
              </p>
            </CardContent>
          </Card>
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
                      formatter={(value: any) => [formatCurrency(value), t('dashboard.revenue')]}
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
                    {lowStockProducts.map((p: any) => {
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
                    {recentReviews.map((r: any) => (
                      <div key={r.id} className="flex items-start space-x-3 border-b border-border pb-3 last:border-0 last:pb-0">
                        <div className="flex bg-yellow-50 text-yellow-600 px-1.5 py-1 rounded-md text-xs font-bold items-center shrink-0">
                          {r.rating} <Star className="h-3 w-3 ml-0.5 fill-yellow-500 text-yellow-500" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-foreground">{r.title}</p>
                          <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">{r.comment}</p>
                          <p className="text-xs text-muted-foreground/70 mt-1">{t('reviews.by', { name: r.reviewer_name })}</p>
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
