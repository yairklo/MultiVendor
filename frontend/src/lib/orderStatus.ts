export const orderStatusClass: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-700',
  pending_payment: 'bg-amber-100 text-amber-700',
  processing: 'bg-blue-100 text-blue-700',
  shipped: 'bg-indigo-100 text-indigo-700',
  completed: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-700',
  expired: 'bg-red-100 text-red-700',
  refunded: 'bg-gray-100 text-gray-700',
}

export const orderStatusLabel: Record<string, string> = {
  pending: 'Pending',
  pending_payment: 'Awaiting Payment',
  processing: 'Processing',
  shipped: 'Shipped',
  completed: 'Completed',
  cancelled: 'Cancelled',
  expired: 'Expired',
  refunded: 'Refunded',
}
