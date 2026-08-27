// Same "safelist" discipline as lib/design-tokens.ts — Tailwind v4 scans source files for
// literal class-name tokens, so every value here MUST be a complete, statically-written
// string; never interpolate `border-${variant}`. This is what lets the AI restyle a product
// card's presentation (product_grid.settings.card_style) without ever letting it emit markup
// or touch the Add to Cart wiring baked into ProductCard itself.
export type CardStyle = 'default' | 'framed' | 'minimal'

export const CARD_STYLE_CLASSES: Record<CardStyle, string> = {
  default: 'rounded-none border-0 bg-transparent shadow-none',
  framed: 'rounded-none border-2 border-gray-900 bg-white shadow-none hover:-translate-y-1 motion-safe:transition-transform motion-safe:duration-300',
  minimal: 'rounded-none border-0 border-b border-gray-200 bg-transparent shadow-none',
}

export function resolveCardStyleClasses(value: unknown): string {
  return typeof value === 'string' && value in CARD_STYLE_CLASSES
    ? CARD_STYLE_CLASSES[value as CardStyle]
    : CARD_STYLE_CLASSES.default
}
