export interface StockVariant {
  stock_quantity?: number
}

export const LOW_STOCK_THRESHOLD = 5

export function totalStock(variants?: StockVariant[] | null): number {
  if (!variants || variants.length === 0) return 0
  return variants.reduce((sum, v) => sum + (v.stock_quantity ?? 0), 0)
}

export type StockLevel = 'out' | 'low' | 'in'

export function stockLevel(quantity: number): StockLevel {
  if (quantity <= 0) return 'out'
  if (quantity <= LOW_STOCK_THRESHOLD) return 'low'
  return 'in'
}

export const stockLevelLabel: Record<StockLevel, string> = {
  out: 'Out of stock',
  low: 'Low stock',
  in: 'In stock',
}

export const stockLevelClass: Record<StockLevel, string> = {
  out: 'bg-red-100 text-red-700',
  low: 'bg-amber-100 text-amber-700',
  in: 'bg-green-100 text-green-700',
}
