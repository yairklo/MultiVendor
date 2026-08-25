import { formatUiDate, formatUiDateTime } from '@/lib/utils'

export type TenantAdmin = {
  id: number
  name: string
  slug: string
  status: 'active' | 'suspended' | 'cancelled' | string
  plan_id: number
  plan_code: string
  plan_name: string
  max_products: number
  product_count: number
  custom_domain: string | null
  show_all_products_in_marketplace: boolean
  stripe_connected: boolean
  created_at: string | null
}

export type PlatformOrder = {
  id: number
  order_number: string
  tenant_id: number
  tenant_name: string
  tenant_slug: string
  status: string
  total_amount: number
  platform_commission: number
  vendor_net_payout: number
  created_at: string | null
}

export type PlatformOverview = {
  tenants_total: number
  tenants_active: number
  tenants_suspended: number
  tenants_cancelled: number
  users_total: number
  products_total: number
  orders_total: number
  gmv: number
  platform_commission: number
  marketplace_vendors: number
  stripe_connected: number
  templates_active: number
  recent_tenants: TenantAdmin[]
  recent_orders: PlatformOrder[]
}

export type SubscriptionPlanAdmin = {
  id: number
  code: string
  name: string
  price_monthly: number
  max_products: number
  max_storage_mb: number
  features_json: Record<string, unknown>
  tenant_count: number
}

export type UserMembership = {
  tenant_id: number
  tenant_name: string
  tenant_slug: string
  role: string
  is_active: boolean
}

export type PlatformUser = {
  id: number
  email: string
  full_name: string
  role: string
  is_active: boolean
  last_login_at: string | null
  created_at: string | null
  memberships: UserMembership[]
}

export type AuditLogItem = {
  id: number
  tenant_id: number | null
  user_id: number | null
  actor_name: string | null
  actor_email: string | null
  action: string
  resource: string
  ip_address: string | null
  details_json: Record<string, unknown> | null
  created_at: string | null
}

export function formatPlatformMoney(amount: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'ILS' }).format(amount || 0)
}

export function formatDate(value: string | null | undefined) {
  return formatUiDate(value, 'en')
}

export function formatDateTime(value: string | null | undefined) {
  return formatUiDateTime(value, 'en')
}

export const nativeSelectClass =
  'h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-sm outline-none transition-colors duration-150 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50'
