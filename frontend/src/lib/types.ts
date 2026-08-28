// Shared response shapes for the core domain objects the API returns.
// Mirrors the backend Pydantic response schemas (server/app/schemas/*.py)
// closely enough for what the frontend actually reads -- not a full 1:1
// codegen, since there's no OpenAPI client generation set up for this repo.

export type OrderStatus =
  | 'pending'
  | 'pending_payment'
  | 'processing'
  | 'shipped'
  | 'completed'
  | 'cancelled'
  | 'expired'
  | 'refunded'

export interface OrderItem {
  id: number
  variant_id: number | null
  product_name: string
  sku: string
  unit_price: number
  quantity: number
  download_url?: string | null
}

export interface OrderPaymentInfo {
  provider: string
  client_secret: string
  publishable_key?: string | null
}

export interface Order {
  id: number
  tenant_id: number
  tenant_slug?: string | null
  customer_id: number
  customer_name?: string | null
  customer_email?: string | null
  order_number: string
  subtotal: number
  discount_amt: number
  shipping_method_id?: number | null
  shipping_fee: number
  total_amount: number
  status: OrderStatus
  order_type: string
  shipping_info?: Record<string, unknown> | null
  created_at: string
  items: OrderItem[]
  payment?: OrderPaymentInfo | null
}

export interface Customer {
  id: number
  email: string
  full_name: string
  created_at: string
  orders_count: number
  total_spent: number
  last_order_at?: string | null
}

// A product/category name or description as the backend stores it --
// {"en": "...", "he": "..."} -- see lib/i18n-text.ts's resolveI18nText.
export type I18nText = Record<string, string>

export interface ProductVariant {
  id?: number
  sku: string
  attributes_json?: Record<string, unknown>
  price_override?: number | null
  stock_quantity: number
}

export interface Product {
  id: number
  tenant_id: number
  category_id?: number | null
  name: I18nText
  slug: string
  description?: I18nText | null
  base_price: number
  is_active: boolean
  show_in_marketplace: boolean
  product_type: string
  digital_file_url?: string | null
  download_limit?: number | null
  is_bundle: boolean
  variants: ProductVariant[]
  primary_image_url?: string | null
  images: string[]
  average_rating?: number | null
  review_count: number
  created_at: string
}

// A product as it appears on the cross-store marketplace listing -- like
// Product, but carries its origin store since browsing spans stores (see
// server/app/schemas/marketplace_schemas.py::MarketplaceProductResponse).
export interface MarketplaceProduct {
  id: number
  tenant_id: number
  tenant_slug: string
  tenant_name: string
  category_id?: number | null
  name: I18nText
  slug: string
  description?: I18nText | null
  base_price: number
  product_type: string
  primary_image_url?: string | null
  images: string[]
  average_rating?: number | null
  review_count: number
  variants: ProductVariant[]
  created_at: string
}

export interface ProductReview {
  id: number
  product_id: number
  product_name?: string | null
  user_id: number
  customer_name?: string | null
  rating: number
  comment?: string | null
  is_approved: boolean
  is_verified_buyer: boolean
  created_at: string
}

export interface Category {
  id: number
  name: I18nText
  slug: string
  parent_id?: number | null
}

export type DiscountType = 'percentage' | 'fixed'

export interface Coupon {
  id: number
  code: string
  discount_type: DiscountType
  discount_val: number
  min_order_amt: number
  usage_limit: number
  used_count: number
  valid_until: string
  is_active: boolean
}

export interface Tenant {
  id: number
  slug: string
  name: string
  plan_code: string
  status: string
  created_at: string
  custom_domain?: string | null
  show_all_products_in_marketplace: boolean
}
