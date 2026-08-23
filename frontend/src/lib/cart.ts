import { apiClient } from '@/lib/api/apiClient'

const CART_STORAGE_KEY = 'mv_cart'

interface StoredCart {
  tenantSlug: string
  cartId: string
  // Capability token proving we're the party this guest cart was created
  // for -- the bare cartId (a client-generated UUID) is not secret, so the
  // backend requires this on every read/mutation of an unclaimed cart. Set
  // once, when the cart is first created; cleared once claimed by a login
  // (the backend then authorizes by session instead).
  cartToken?: string
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

export function cartTokenHeaders(): Record<string, string> {
  const stored = readStoredCart()
  return stored?.cartToken ? { 'X-Cart-Token': stored.cartToken } : {}
}

export async function addItemToCart(tenantSlug: string, variantId: number, quantity = 1) {
  const cart = getOrCreateCart(tenantSlug)
  const result = await apiClient(`/api/v1/store/${tenantSlug}/cart/${cart.cartId}/items`, {
    method: 'POST',
    headers: cartTokenHeaders(),
    body: JSON.stringify({ variant_id: variantId, quantity }),
  })
  // Only present the first time this cart is created (a fresh guest cart) --
  // persist it so subsequent requests can prove ownership of it.
  if (result?.cart_token) {
    writeStoredCart({ ...cart, cartToken: result.cart_token })
  }
  return cart
}

export async function fetchCart(tenantSlug: string, cartId: string): Promise<Cart> {
  return apiClient(`/api/v1/store/${tenantSlug}/cart/${cartId}`, {
    headers: cartTokenHeaders(),
  })
}

export async function updateItemQuantity(tenantSlug: string, cartId: string, itemId: number, quantity: number) {
  return apiClient(`/api/v1/store/${tenantSlug}/cart/${cartId}/items/${itemId}`, {
    method: 'PATCH',
    headers: cartTokenHeaders(),
    body: JSON.stringify({ quantity }),
  })
}

export async function removeCartItem(tenantSlug: string, cartId: string, itemId: number) {
  return apiClient(`/api/v1/store/${tenantSlug}/cart/${cartId}/items/${itemId}`, {
    method: 'DELETE',
    headers: cartTokenHeaders(),
  })
}
