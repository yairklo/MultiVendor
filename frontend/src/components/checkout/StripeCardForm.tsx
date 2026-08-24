'use client'

import React, { useEffect, useRef, useState } from 'react'
import type { Stripe, StripeCardElement } from '@stripe/stripe-js'
import { loadStripe } from '@stripe/stripe-js'

// One loadStripe() call per publishable key for the lifetime of the tab --
// Stripe's own recommendation, and avoids re-injecting stripe.js on every render.
const stripePromiseCache = new Map<string, Promise<Stripe | null>>()
function getStripe(publishableKey: string): Promise<Stripe | null> {
  if (!stripePromiseCache.has(publishableKey)) {
    stripePromiseCache.set(publishableKey, loadStripe(publishableKey))
  }
  return stripePromiseCache.get(publishableKey)!
}

const POLL_INTERVAL_MS = 2000
const POLL_TIMEOUT_MS = 30000

function sleep(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

interface StripeCardFormProps {
  clientSecret: string
  publishableKey: string
  // Stripe confirming the card on the CLIENT side is not the same thing as
  // this app's order being paid -- that only happens once the Stripe
  // webhook has verified the event server-side and flipped the order's
  // status. This polls the caller's own "is it processing yet?" check
  // rather than trusting confirmCardPayment's result alone, which is what
  // onSuccess is gated on.
  checkPaid: () => Promise<boolean>
  onSuccess: () => void
  onError: (message: string) => void
}

// Deliberately built on the vanilla @stripe/stripe-js API (not
// @stripe/react-stripe-js) -- this is the one place in the app that needs
// Stripe at all, so a single mounted CardElement is simpler than adding a
// whole <Elements> provider tree for one form.
export function StripeCardForm({ clientSecret, publishableKey, checkPaid, onSuccess, onError }: StripeCardFormProps) {
  const cardMountRef = useRef<HTMLDivElement>(null)
  const stripeRef = useRef<Stripe | null>(null)
  const cardElementRef = useRef<StripeCardElement | null>(null)
  const [ready, setReady] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [confirming, setConfirming] = useState(false)

  useEffect(() => {
    let cancelled = false
    getStripe(publishableKey).then((stripe) => {
      if (cancelled || !stripe || !cardMountRef.current) return
      stripeRef.current = stripe
      const elements = stripe.elements()
      const card = elements.create('card')
      card.mount(cardMountRef.current)
      cardElementRef.current = card
      setReady(true)
    })
    return () => {
      cancelled = true
      cardElementRef.current?.unmount()
    }
    // publishableKey is stable for the lifetime of one checkout/pay flow.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const stripe = stripeRef.current
    const card = cardElementRef.current
    if (!stripe || !card) return

    setSubmitting(true)
    try {
      const result = await stripe.confirmCardPayment(clientSecret, {
        payment_method: { card },
      })
      if (result.error) {
        onError(result.error.message || 'Payment failed.')
        return
      }
      if (result.paymentIntent?.status !== 'succeeded' && result.paymentIntent?.status !== 'processing') {
        onError('Payment was not completed.')
        return
      }

      // Stripe accepted the card -- now wait for OUR webhook to have
      // actually verified it and flipped the order server-side before
      // telling the caller it's safe to treat this as paid.
      setConfirming(true)
      const deadline = Date.now() + POLL_TIMEOUT_MS
      let paid = false
      while (Date.now() < deadline) {
        if (await checkPaid()) {
          paid = true
          break
        }
        await sleep(POLL_INTERVAL_MS)
      }

      if (paid) {
        onSuccess()
      } else {
        onError('Payment is still being confirmed. Check My Orders shortly -- it can take a moment to finalize.')
      }
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Payment failed.')
    } finally {
      setSubmitting(false)
      setConfirming(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div ref={cardMountRef} className="border border-input rounded-lg px-3 py-3 bg-card transition-shadow focus-within:ring-2 focus-within:ring-ring" />
      <button
        type="submit"
        disabled={!ready || submitting}
        className="w-full bg-primary text-primary-foreground py-3 rounded-xl font-bold transition-all duration-150 hover:bg-primary/90 active:scale-[0.98] disabled:opacity-70"
      >
        {confirming ? 'Confirming payment...' : submitting ? 'Processing...' : 'Pay with Card'}
      </button>
    </form>
  )
}
