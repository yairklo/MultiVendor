// Same "safelist" discipline as lib/design-tokens.ts — Tailwind v4 scans source files for
// literal class-name tokens, so every value here MUST be a complete, statically-written
// string; never interpolate `border-${variant}`. This is what lets the AI restyle a product
// card's presentation (product_grid.settings.card_style) without ever letting it emit markup
// or touch the Add to Cart wiring baked into ProductCard itself.
export type CardStyle = 'default' | 'framed' | 'minimal' | 'glass' | 'elevated'

export const CARD_STYLE_CLASSES: Record<CardStyle, string> = {
  default: 'rounded-xl border border-gray-100 bg-white shadow-sm hover:shadow-lg transition-shadow duration-300',
  framed: 'rounded-2xl border-2 border-gray-900 bg-white shadow-none hover:-translate-y-1 transition-transform duration-300',
  minimal: 'rounded-none border-0 border-b border-gray-200 bg-transparent shadow-none',
  glass: 'rounded-2xl border border-border/40 backdrop-blur-md bg-background/80 shadow-apple-glass transition-all duration-300',
  elevated: 'rounded-xl bg-card shadow-apple-elevated shadow-apple-inset transition-all duration-300',
}

export function resolveCardStyleClasses(value: unknown): string {
  return typeof value === 'string' && value in CARD_STYLE_CLASSES
    ? CARD_STYLE_CLASSES[value as CardStyle]
    : CARD_STYLE_CLASSES.default
}
