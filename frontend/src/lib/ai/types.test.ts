import { describe, it, expect } from 'vitest'
import { CARD_STYLE_CLASSES } from '../product-card-styles'

describe('Card Styles allow-list sync', () => {
  it('should include all required Apple UI card styles', () => {
    expect(CARD_STYLE_CLASSES).toHaveProperty('default')
    expect(CARD_STYLE_CLASSES).toHaveProperty('framed')
    expect(CARD_STYLE_CLASSES).toHaveProperty('minimal')
    expect(CARD_STYLE_CLASSES).toHaveProperty('glass')
    expect(CARD_STYLE_CLASSES).toHaveProperty('elevated')
  })
})
