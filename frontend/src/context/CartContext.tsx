'use client'

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import {
  Cart,
  addItemToCart,
  clearCart as clearStoredCart,
  fetchCart,
  getActiveCart,
  removeCartItem,
  updateItemQuantity,
} from '@/lib/cart'

interface CartContextValue {
  cart: Cart | null
  loading: boolean
  isOpen: boolean
  openDrawer: () => void
  closeDrawer: () => void
  addItem: (tenantSlug: string, variantId: number, quantity?: number) => Promise<void>
  incrementItem: (itemId: number) => Promise<void>
  decrementItem: (itemId: number) => Promise<void>
  removeItem: (itemId: number) => Promise<void>
  refresh: () => Promise<void>
  clear: () => void
}

const CartContext = createContext<CartContextValue | null>(null)

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [cart, setCart] = useState<Cart | null>(null)
  const [loading, setLoading] = useState(true)
  const [isOpen, setIsOpen] = useState(false)

  const refresh = useCallback(async () => {
    const active = getActiveCart()
    if (!active) {
      setCart(null)
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const data = await fetchCart(active.tenantSlug, active.cartId)
      setCart(data)
    } catch (e) {
      // A stored cart can go stale (e.g. the tenant/store it pointed at no
      // longer exists). There's nothing to recover — drop it rather than
      // leaving the app stuck on a cart that will never load.
      console.error('Failed to load cart, clearing stale cart state:', e)
      clearStoredCart()
      setCart(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const addItem = useCallback(async (tenantSlug: string, variantId: number, quantity = 1) => {
    await addItemToCart(tenantSlug, variantId, quantity)
    await refresh()
  }, [refresh])

  const incrementItem = useCallback(async (itemId: number) => {
    const active = getActiveCart()
    const item = cart?.items.find(i => i.id === itemId)
    if (!active || !item) return
    await updateItemQuantity(active.tenantSlug, active.cartId, itemId, item.quantity + 1)
    await refresh()
  }, [cart, refresh])

  const decrementItem = useCallback(async (itemId: number) => {
    const active = getActiveCart()
    const item = cart?.items.find(i => i.id === itemId)
    if (!active || !item) return
    if (item.quantity <= 1) {
      await removeCartItem(active.tenantSlug, active.cartId, itemId)
    } else {
      await updateItemQuantity(active.tenantSlug, active.cartId, itemId, item.quantity - 1)
    }
    await refresh()
  }, [cart, refresh])

  const removeItem = useCallback(async (itemId: number) => {
    const active = getActiveCart()
    if (!active) return
    await removeCartItem(active.tenantSlug, active.cartId, itemId)
    await refresh()
  }, [refresh])

  const clear = useCallback(() => {
    clearStoredCart()
    setCart(null)
  }, [])

  const value: CartContextValue = {
    cart,
    loading,
    isOpen,
    openDrawer: () => setIsOpen(true),
    closeDrawer: () => setIsOpen(false),
    addItem,
    incrementItem,
    decrementItem,
    removeItem,
    refresh,
    clear,
  }

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext)
  if (!ctx) throw new Error('useCart must be used within a CartProvider')
  return ctx
}
