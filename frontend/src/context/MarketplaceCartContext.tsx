'use client'

import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import {
  MarketplaceCart,
  addItemToMarketplaceCart,
  clearMarketplaceCart as clearStoredMarketplaceCart,
  fetchMarketplaceCart,
  getActiveMarketplaceCart,
  removeMarketplaceCartItem,
  updateMarketplaceCartItemQuantity,
} from '@/lib/marketplace-cart'
import { ApiError } from '@/lib/api/apiClient'

interface MarketplaceCartContextValue {
  cart: MarketplaceCart | null
  loading: boolean
  isOpen: boolean
  pendingItemIds: Set<number>
  openDrawer: () => void
  closeDrawer: () => void
  addItem: (variantId: number, quantity?: number) => Promise<void>
  incrementItem: (itemId: number) => Promise<void>
  decrementItem: (itemId: number) => Promise<void>
  removeItem: (itemId: number) => Promise<void>
  refresh: () => Promise<void>
  clear: () => void
}

const MarketplaceCartContext = createContext<MarketplaceCartContextValue | null>(null)

/** Cross-vendor equivalent of CartContext -- same shape and refresh-after-every-mutation
 * convention, just not tenant-scoped (see lib/marketplace-cart.ts). Kept as a separate
 * provider/context rather than extending CartContext since the two carts are genuinely
 * different resources on the backend (marketplace_cart_items vs. carts/cart_items), with
 * different checkout endpoints and different order-splitting behavior. */
export function MarketplaceCartProvider({ children }: { children: React.ReactNode }) {
  const [cart, setCart] = useState<MarketplaceCart | null>(null)
  const [loading, setLoading] = useState(true)
  const [isOpen, setIsOpen] = useState(false)
  const [pendingItemIds, setPendingItemIds] = useState<Set<number>>(new Set())
  const pendingRef = useRef<Set<number>>(new Set())

  const refresh = useCallback(async () => {
    const active = getActiveMarketplaceCart()
    if (!active) {
      setCart(null)
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const data = await fetchMarketplaceCart(active.cartId)
      setCart(data)
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 404)) {
        console.error(`Failed to load marketplace cart (${e instanceof ApiError ? e.status : 'unknown'}), clearing stale cart state`)
      }
      clearStoredMarketplaceCart()
      setCart(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // Standard fetch-on-mount effect -- refresh's first synchronous step is
    // setLoading/setCart, same "start loading" pattern React's own data
    // fetching docs example uses.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh()
  }, [refresh])

  const addItem = useCallback(async (variantId: number, quantity = 1) => {
    await addItemToMarketplaceCart(variantId, quantity)
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
      const active = getActiveMarketplaceCart()
      const item = cart?.items.find(i => i.id === itemId)
      if (!active || !item) return
      await updateMarketplaceCartItemQuantity(active.cartId, itemId, item.quantity + 1)
      await refresh()
    })
  }, [cart, refresh, withItemLock])

  const decrementItem = useCallback(async (itemId: number) => {
    await withItemLock(itemId, async () => {
      const active = getActiveMarketplaceCart()
      const item = cart?.items.find(i => i.id === itemId)
      if (!active || !item) return
      if (item.quantity <= 1) {
        await removeMarketplaceCartItem(active.cartId, itemId)
      } else {
        await updateMarketplaceCartItemQuantity(active.cartId, itemId, item.quantity - 1)
      }
      await refresh()
    })
  }, [cart, refresh, withItemLock])

  const removeItem = useCallback(async (itemId: number) => {
    await withItemLock(itemId, async () => {
      const active = getActiveMarketplaceCart()
      if (!active) return
      await removeMarketplaceCartItem(active.cartId, itemId)
      await refresh()
    })
  }, [refresh, withItemLock])

  const clear = useCallback(() => {
    clearStoredMarketplaceCart()
    setCart(null)
  }, [])

  const value: MarketplaceCartContextValue = {
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

  return <MarketplaceCartContext.Provider value={value}>{children}</MarketplaceCartContext.Provider>
}

export function useMarketplaceCart(): MarketplaceCartContextValue {
  const ctx = useContext(MarketplaceCartContext)
  if (!ctx) throw new Error('useMarketplaceCart must be used within a MarketplaceCartProvider')
  return ctx
}
