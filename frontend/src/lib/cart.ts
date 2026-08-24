import { apiClient } from '@/lib/api/apiClient'

const CART_STORAGE_KEY = 'mv_cart'

interface StoredCart {
  tenantSlug: string
  cartId: string
}

export interface CartItem {
  id: number
  variant_id: number
  product_name: string
  product_type: 'physical' | 'digital' | 'service'
  sku: string
  attributes: Record<string, unknown>
  unit_price: number
  quantity: number
  total_price: number
  image_url?: string | null
}

export interface Cart {
  cart_id: string
  tenant_id: number
  items: CartItem[]
  subtotal: number
}

function readStoredCart(): StoredCart | null {
  if (typeof window === 'undefined') return null
  const raw = window.localStorage.getItem(CART_STORAGE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as StoredCart
  } catch {
    return null
  }
}

function writeStoredCart(cart: StoredCart) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart))
}

// A cart is scoped to one tenant at a time. Switching tenants starts a fresh cart.
export function getOrCreateCart(tenantSlug: string): StoredCart {
  const existing = readStoredCart()
  if (existing && existing.tenantSlug === tenantSlug) return existing

  const created: StoredCart = { tenantSlug, cartId: crypto.randomUUID() }
  writeStoredCart(created)
  return created
}

export function getActiveCart(): StoredCart | null {
  return readStoredCart()
}

export function clearCart() {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(CART_STORAGE_KEY)
}

// The guest cart's capability token (proving we're the party an unclaimed
// cart was created for) lives entirely in a `cart_token` HttpOnly cookie
// the backend sets/clears itself (see server/app/routers/cart_router.py) --
// this file never reads, stores, or forwards it. apiClient sends
// credentials: 'include' so the browser attaches that cookie automatically;
// JS (and therefore XSS) never has access to the value at all.

export async function addItemToCart(tenantSlug: string, variantId: number, quantity = 1) {
  const cart = getOrCreateCart(tenantSlug)
  await apiClient(`/api/v1/store/${tenantSlug}/cart/${cart.cartId}/items`, {
    method: 'POST',
    body: JSON.stringify({ variant_id: variantId, quantity }),
  })
  return cart
}

export async function fetchCart(tenantSlug: string, cartId: string): Promise<Cart> {
  return apiClient(`/api/v1/store/${tenantSlug}/cart/${cartId}`)
}

export async function updateItemQuantity(tenantSlug: string, cartId: string, itemId: number, quantity: number) {
  return apiClient(`/api/v1/store/${tenantSlug}/cart/${cartId}/items/${itemId}`, {
    method: 'PATCH',
    body: JSON.stringify({ quantity }),
  })
}

export async function removeCartItem(tenantSlug: string, cartId: string, itemId: number) {
  return apiClient(`/api/v1/store/${tenantSlug}/cart/${cartId}/items/${itemId}`, {
    method: 'DELETE',
  })
}
