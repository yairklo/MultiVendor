import { CSSProperties } from 'react'

// Section settings are free-form (Record<string, any>), so the AI can write
// color/theme info under any of several plausible keys. This maps whichever
// one is present to CSS custom properties that section components apply to
// their root element, so a "make it red" edit actually renders instead of
// silently updating JSON no component reads.
const BACKGROUND_KEYS = ['background_color', 'background', 'theme_color', 'theme']
const TEXT_KEYS = ['text_color', 'color']
const FONT_KEYS = ['font_family']

function firstStringValue(settings: Record<string, any>, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = settings[key]
    if (typeof value === 'string' && value.trim().length > 0) return value
  }
  return undefined
}

export function getSectionThemeStyle(settings: Record<string, any>): CSSProperties {
  const style: Record<string, string> = {}
  const background = firstStringValue(settings, BACKGROUND_KEYS)
  const text = firstStringValue(settings, TEXT_KEYS)
  const font = firstStringValue(settings, FONT_KEYS)
  if (background) style['--section-bg'] = background
  if (text) style['--section-text'] = text
  if (font) style['--section-font'] = font
  return style as CSSProperties
}
