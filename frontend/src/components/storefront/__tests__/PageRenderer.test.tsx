import { render, screen } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import { PageRenderer } from '../PageRenderer'
import { CartProvider } from '@/context/CartContext'
import { StorePageSchema } from '@/lib/ai/types'

// Guards against XSS if the AI ever hallucinates (or is prompted to produce)
// raw HTML/script in a text field. Every section type renders AI-controlled
// text through plain JSX {…} interpolation — this proves none of them use
// dangerouslySetInnerHTML or otherwise turn a string into live markup.
const XSS_PAYLOAD = '<img src=x onerror="window.__xss_fired = true">'
const SCRIPT_PAYLOAD = '<script>window.__xss_fired = true</script>'

const page: StorePageSchema = {
  page_key: 'xss-test',
  page_type: 'static_page',
  title: 'XSS Test',
  sections: [
    { id: 's1', type: 'hero_banner', settings: { headline: XSS_PAYLOAD, size: 'medium' } },
    { id: 's2', type: 'text_block', settings: { heading: SCRIPT_PAYLOAD, body: XSS_PAYLOAD } },
    { id: 's3', type: 'video_embed', settings: { title: XSS_PAYLOAD } },
    { id: 's4', type: 'gallery', settings: {} },
    {
      id: 's5',
      type: 'table',
      settings: { title: XSS_PAYLOAD, headers: [XSS_PAYLOAD], rows: [[SCRIPT_PAYLOAD]] },
    },
    {
      id: 's6',
      type: 'button_group',
      settings: { buttons: [{ label: XSS_PAYLOAD, actionType: 'NAVIGATE', actionPayload: { href: '/shop' } }] },
    },
    { id: 's7', type: 'product_grid', settings: { title: XSS_PAYLOAD, columns: 2 } },
  ],
}

describe('PageRenderer XSS safety', () => {
  beforeEach(() => {
    ;(window as any).__xss_fired = false
  })

  it('never turns AI-controlled text into live HTML/script across any section type', () => {
    const { container } = render(
      <CartProvider>
        <PageRenderer page={page} />
      </CartProvider>
    )

    // No script ever executed, in any section.
    expect((window as any).__xss_fired).toBe(false)

    // No section rendered the payload as a real element — it stayed inert text.
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('script')).toBeNull()

    // The payload is still shown to the user, just safely as literal text
    // (proves it was escaped, not silently stripped).
    expect(screen.getAllByText(XSS_PAYLOAD, { exact: false }).length).toBeGreaterThan(0)
  })
})
