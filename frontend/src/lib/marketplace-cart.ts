import { apiClient } from '@/lib/api/apiClient'

const CART_STORAGE_KEY = 'mv_marketplace_cart'

interface StoredMarketplaceCart {
  cartId: string
}

export interface MarketplaceCartItem {
  id: number
  tenant_id: number
  tenant_slug: string
  tenant_name: string
  variant_id: number
  product_name: string
  sku: string
  unit_price: number
  quantity: number
  total_price: number
  image_url?: string | null
}

export interface MarketplaceCart {
  cart_id: string
  items: MarketplaceCartItem[]
  subtotal: number
  vendor_count: number
}

function readStoredCart(): StoredMarketplaceCart | null {
  if (typeof window === 'undefined') return null
  const raw = window.localStorage.getItem(CART_STORAGE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as StoredMarketplaceCart
  } catch {
    return null
  }
}

function writeStoredCart(cart: StoredMarketplaceCart) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart))
}

// Unlike lib/cart.ts's single-store cart, this one is NOT scoped to a tenant
// -- one cart id can hold items from any number of vendors at once (see
// marketplace_cart_items on the backend, which has no parent tenant-scoped
// Cart row at all).
export function getOrCreateMarketplaceCart(): StoredMarketplaceCart {
  const existing = readStoredCart()
  if (existing) return existing

  const created: StoredMarketplaceCart = { cartId: crypto.randomUUID() }
  writeStoredCart(created)
  return created
}

export function getActiveMarketplaceCart(): StoredMarketplaceCart | null {
  return readStoredCart()
}

export function clearMarketplaceCart() {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(CART_STORAGE_KEY)
}

export async function addItemToMarketplaceCart(variantId: number, quantity = 1) {
  const cart = getOrCreateMarketplaceCart()
  await apiClient(`/api/v1/marketplace/cart/${cart.cartId}/items`, {
    method: 'POST',
    body: JSON.stringify({ variant_id: variantId, quantity }),
  })
  return cart
}

export async function fetchMarketplaceCart(cartId: string): Promise<MarketplaceCart> {
  return apiClient(`/api/v1/marketplace/cart/${cartId}`)
}

export async function updateMarketplaceCartItemQuantity(cartId: string, itemId: number, quantity: number) {
  return apiClient(`/api/v1/marketplace/cart/${cartId}/items/${itemId}`, {
    method: 'PATCH',
    body: JSON.stringify({ quantity }),
  })
}

export async function removeMarketplaceCartItem(cartId: string, itemId: number) {
  return apiClient(`/api/v1/marketplace/cart/${cartId}/items/${itemId}`, {
    method: 'DELETE',
  })
}
