import { DesignVariant } from '@/lib/ai/types'

// Tailwind v4 has no JS `safelist` config — it scans source files for literal class-name
// tokens at build time. Every value below MUST be a complete, statically-written string;
// never interpolate `bg-${variant}` anywhere, that produces a class Tailwind can't see and
// therefore never generates. This map is the "safelist": as long as these literal strings
// live in a scanned .ts file, the corresponding CSS always exists.
export const DESIGN_TOKEN_CLASSES: Record<DesignVariant, string> = {
  primary: 'bg-primary text-primary-foreground rounded-2xl p-6',
  accent: 'bg-accent text-accent-foreground rounded-2xl p-6',
  secondary: 'bg-secondary text-secondary-foreground rounded-2xl p-6',
  muted: 'bg-muted text-muted-foreground rounded-2xl p-6',
  neutral: 'bg-white border border-gray-200 rounded-2xl p-6',
}

/** Falls back to 'neutral' for anything unrecognized — defense-in-depth; the backend's
 * own allow-list clamp in `_sanitize_design_variant_settings` is the real enforcement gate. */
export function resolveDesignVariantClasses(value: unknown): string {
  return typeof value === 'string' && value in DESIGN_TOKEN_CLASSES
    ? DESIGN_TOKEN_CLASSES[value as DesignVariant]
    : DESIGN_TOKEN_CLASSES.neutral
}
