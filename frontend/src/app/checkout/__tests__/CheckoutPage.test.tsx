import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach } from 'vitest'
import CheckoutPage from '../page'
import { http, HttpResponse } from 'msw'
import { server } from '../../../mocks/server'

describe('CheckoutPage', () => {
  beforeEach(() => {
    server.use(
      http.post('http://localhost:3000/api/v1/cart/checkout', () => {
        return HttpResponse.json({ success: true, orderId: 123 })
      })
    )
  })

  it('renders item summary, shipping methods, and coupon inputs', () => {
    render(<CheckoutPage />)
    expect(screen.getByTestId('item-summary')).toBeInTheDocument()
    expect(screen.getByTestId('shipping-methods')).toBeInTheDocument()
    expect(screen.getByTestId('coupon-input')).toBeInTheDocument()
  })

  it('submits checkout and sends payload to POST /api/v1/cart/checkout', async () => {
    const user = userEvent.setup()
    render(<CheckoutPage />)
    
    const submitButton = screen.getByRole('button', { name: /place order/i })
    await user.click(submitButton)
    
    expect(await screen.findByText(/order placed/i)).toBeInTheDocument()
  })
})

