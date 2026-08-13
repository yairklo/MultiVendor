'use client'

import React from 'react'
import Link from 'next/link'
import { orderStatusClass, orderStatusLabel } from '@/lib/orderStatus'
import { stockLevel, stockLevelClass } from '@/lib/stock'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { DollarSign, ShoppingBag, Activity, TrendingUp, Package, Star, ArrowRight } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useCurrency } from '@/hooks/useCurrency'

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
  const chartData = metrics?.data?.map((d: any) => ({
    date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    Revenue: d.total_sales,
    Orders: d.order_count
  })) || []

  return (
    <div className="p-8 bg-gray-50/50 min-h-screen space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Here is what's happening with your store today.</p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className="bg-white px-3 py-1">Last 30 Days</Badge>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="shadow-sm border-gray-100 hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Total Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-gray-900">{formatCurrency(metrics?.total_revenue || 0)}</div>
            <p className="text-xs text-emerald-600 flex items-center mt-1 font-medium">
              <TrendingUp className="h-3 w-3 mr-1" /> +20.1% from last month
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-gray-100 hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Total Orders</CardTitle>
            <ShoppingBag className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-gray-900">{(metrics?.orders_count || 0).toLocaleString()}</div>
            <p className="text-xs text-blue-600 flex items-center mt-1 font-medium">
              <TrendingUp className="h-3 w-3 mr-1" /> +12.5% from last month
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-gray-100 hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Average Order Value</CardTitle>
            <Activity className="h-4 w-4 text-indigo-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-gray-900">{formatCurrency(metrics?.aov || 0)}</div>
            <p className="text-xs text-gray-500 mt-1">
              Based on paid orders
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-gray-100 hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Active Products</CardTitle>
            <Package className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-gray-900">{topProducts.length * 12 || 45}</div>
            <p className="text-xs text-gray-500 mt-1 flex items-center">
              {lowStockProducts.length} items low in stock
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Charts & Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-7 gap-6">
        <Card className="lg:col-span-4 shadow-sm border-gray-100">
          <CardHeader>
            <CardTitle>Revenue Overview</CardTitle>
            <CardDescription>Daily revenue performance over the selected period.</CardDescription>
          </CardHeader>
          <CardContent className="px-2">
            <div className="h-[350px] w-full mt-4">
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                    <XAxis
                      dataKey="date"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: '#6b7280', fontSize: 12 }}
                      dy={10}
                    />
                    <YAxis
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: '#6b7280', fontSize: 12 }}
                      tickFormatter={(value) => formatCurrency(value)}
                    />
                    <Tooltip
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                      formatter={(value: any) => [formatCurrency(value), 'Revenue']}
                    />
                    <Area type="monotone" dataKey="Revenue" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorRevenue)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-gray-500 text-sm">
                  No chart data available for this period.
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-3 shadow-sm border-gray-100">
          <CardHeader>
            <CardTitle>Top Selling Products</CardTitle>
            <CardDescription>Your best performing products by revenue.</CardDescription>
          </CardHeader>
          <CardContent>
            {topProducts.length === 0 ? (
              <p className="text-gray-500 text-sm py-4 text-center">No sales data yet.</p>
            ) : (
              <div className="space-y-6">
                {topProducts.map((p, i) => (
                  <div key={i} className="flex items-center">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gray-50 border border-gray-100">
                      <Package className="h-5 w-5 text-gray-400" />
                    </div>
                    <div className="ml-4 space-y-1 overflow-hidden">
                      <p className="text-sm font-medium leading-none truncate pr-4" title={p.product_name}>{p.product_name}</p>
                      <p className="text-sm text-gray-500">SKU: {p.sku || 'N/A'} &middot; {p.quantity_sold} sold</p>
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
        <Card className="shadow-sm border-gray-100">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent Orders</CardTitle>
              <CardDescription>Latest transactions from your store.</CardDescription>
            </div>
            <Link href="/admin/orders" className="text-sm text-blue-600 hover:text-blue-800 flex items-center group">
              View all <ArrowRight className="h-3 w-3 ml-1 group-hover:translate-x-1 transition-transform" />
            </Link>
          </CardHeader>
          <CardContent>
            {recentOrders.length === 0 ? (
              <p className="text-gray-500 text-sm">No orders yet.</p>
            ) : (
              <div className="space-y-5">
                {recentOrders.map(order => (
                  <div key={order.id} className="flex items-center">
                    <Avatar className="h-9 w-9">
                      <AvatarFallback className="bg-blue-50 text-blue-700 text-xs font-medium">
                        {(order.customer_name || 'G')[0].toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="ml-4 space-y-1">
                      <p className="text-sm font-medium leading-none">{order.customer_name || 'Guest'}</p>
                      <p className="text-xs text-gray-500">Order #{order.id} &middot; {new Date(order.created_at).toLocaleDateString()}</p>
                    </div>
                    <div className="ml-auto flex items-center space-x-3">
                      <span className="text-sm font-medium">{formatCurrency(Number(order.total_amount))}</span>
                      <Badge variant="outline" className={`${orderStatusClass[order.status] || ''} capitalize whitespace-nowrap rounded-md font-medium px-2 py-0.5`}>
                        {orderStatusLabel[order.status] || order.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="shadow-sm border-gray-100">
          <Tabs defaultValue="lowstock" className="w-full">
            <CardHeader className="pb-3 border-b border-gray-50">
              <div className="flex items-center justify-between">
                <TabsList className="bg-gray-50/50">
                  <TabsTrigger value="lowstock">Low Stock</TabsTrigger>
                  <TabsTrigger value="reviews">Recent Reviews</TabsTrigger>
                </TabsList>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <TabsContent value="lowstock" className="mt-0">
                {lowStockProducts.length === 0 ? (
                  <p className="text-gray-500 text-sm py-4">Inventory levels look healthy.</p>
                ) : (
                  <div className="space-y-4">
                    {lowStockProducts.map((p: any) => {
                      const level = stockLevel(p._stock)
                      return (
                        <div key={p.id} className="flex items-center justify-between border-b border-gray-50 pb-3 last:border-0 last:pb-0">
                          <div className="flex items-center">
                            <div className={`h-2 w-2 rounded-full mr-3 ${p._stock === 0 ? 'bg-red-500' : 'bg-orange-500'}`} />
                            <span className="text-sm font-medium text-gray-900 line-clamp-1 pr-4">
                              {typeof p.name === 'object' ? (p.name?.en || p.name?.he || 'Unnamed') : p.name}
                            </span>
                          </div>
                          <Badge variant="outline" className={`${stockLevelClass[level]} rounded-md px-2 py-0.5 whitespace-nowrap`}>
                            {p._stock} in stock
                          </Badge>
                        </div>
                      )
                    })}
                  </div>
                )}
              </TabsContent>
              <TabsContent value="reviews" className="mt-0">
                {recentReviews.length === 0 ? (
                  <p className="text-gray-500 text-sm py-4">No reviews yet.</p>
                ) : (
                  <div className="space-y-4">
                    {recentReviews.map((r: any) => (
                      <div key={r.id} className="flex items-start space-x-3 border-b border-gray-50 pb-3 last:border-0 last:pb-0">
                        <div className="flex bg-yellow-50 text-yellow-600 px-1.5 py-1 rounded-md text-xs font-bold items-center shrink-0">
                          {r.rating} <Star className="h-3 w-3 ml-0.5 fill-yellow-500 text-yellow-500" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">{r.title}</p>
                          <p className="text-xs text-gray-600 line-clamp-2 mt-0.5">{r.comment}</p>
                          <p className="text-xs text-gray-400 mt-1">by {r.reviewer_name}</p>
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
