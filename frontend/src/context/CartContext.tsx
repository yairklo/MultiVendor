'use client'

import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import {
  Cart,
  addItemToCart,
  clearCart as clearStoredCart,
  fetchCart,
  getActiveCart,
  removeCartItem,
  updateItemQuantity,
} from '@/lib/cart'
import { ApiError } from '@/lib/api/apiClient'

interface CartContextValue {
  cart: Cart | null
  loading: boolean
  isOpen: boolean
  pendingItemIds: Set<number>
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
  const [pendingItemIds, setPendingItemIds] = useState<Set<number>>(new Set())
  // Mirrors pendingItemIds but readable synchronously inside the same tick a
  // click handler runs in, so a second click on the same item before React
  // re-renders is still rejected (state alone lags one render behind).
  const pendingRef = useRef<Set<number>>(new Set())

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
      // A stored cart can go stale (never created on the server, or the
      // tenant it pointed at no longer exists). Drop it rather than leaving
      // the app stuck. Don't pass the Error to console.error — Next.js
      // treats that as a runtime overlay even though this path is handled.
      if (!(e instanceof ApiError && e.status === 404)) {
        console.error(`Failed to load cart (${e instanceof ApiError ? e.status : 'unknown'}), clearing stale cart state`)
      }
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

  const withItemLock = useCallback(async (itemId: number, run: () => Promise<void>) => {
    if (pendingRef.current.has(itemId)) return
    pendingRef.current.add(itemId)
    setPendingItemIds(new Set(pendingRef.current))
    try {
      await run()
    } finally {
      pendingRef.current.delete(itemId)
      setPendingItemIds(new Set(pendingRef.current))
    }
  }, [])

  const incrementItem = useCallback(async (itemId: number) => {
    await withItemLock(itemId, async () => {
      const active = getActiveCart()
      const item = cart?.items.find(i => i.id === itemId)
      if (!active || !item) return
      await updateItemQuantity(active.tenantSlug, active.cartId, itemId, item.quantity + 1)
      await refresh()
    })
  }, [cart, refresh, withItemLock])

  const decrementItem = useCallback(async (itemId: number) => {
    await withItemLock(itemId, async () => {
      const active = getActiveCart()
      const item = cart?.items.find(i => i.id === itemId)
      if (!active || !item) return
      if (item.quantity <= 1) {
        await removeCartItem(active.tenantSlug, active.cartId, itemId)
      } else {
        await updateItemQuantity(active.tenantSlug, active.cartId, itemId, item.quantity - 1)
      }
      await refresh()
    })
  }, [cart, refresh, withItemLock])

  const removeItem = useCallback(async (itemId: number) => {
    await withItemLock(itemId, async () => {
      const active = getActiveCart()
      if (!active) return
      await removeCartItem(active.tenantSlug, active.cartId, itemId)
      await refresh()
    })
  }, [refresh, withItemLock])

  const clear = useCallback(() => {
    clearStoredCart()
    setCart(null)
  }, [])

  const value: CartContextValue = {
    cart,
    loading,
    isOpen,
    pendingItemIds,
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
