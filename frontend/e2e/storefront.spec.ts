import { test, expect } from '@playwright/test';

test.describe('Storefront & Checkout Flow', () => {
  const tenantSlug = 'test-tenant';
  const productName = `Storefront E2E Product ${Date.now()}`; // Unique name

  test.beforeEach(async ({ page }) => {
    // We need at least one product to test the storefront. Let's create one.
    await page.goto('/admin/products/new');
    await page.getByLabel(/Product Name/i).fill(productName);
    await page.getByLabel(/slug/i).fill(`storefront-e2e-${Date.now()}`);
    await page.getByLabel(/price/i).fill('19.99');
    await page.getByRole('button', { name: /save product/i }).click();
    await page.waitForURL(/\/admin\/products$/);
  });

  test('Browse and add to cart', async ({ page }) => {
    await page.goto(`/store/${tenantSlug}`);
    
    // Verify product is visible
    await expect(page.locator(`text=${productName}`).first()).toBeVisible({ timeout: 10000 });
    
    // Click Add to Cart
    await page.getByRole('button', { name: /add to cart/i }).first().click();
    
    // Verify cart drawer updates
    await expect(page.locator('text=Cart (1)').first()).toBeVisible();
  });

  test('Checkout flow', async ({ page, request }) => {
    // Checking out is allowed for a tenant_admin (a store owner testing
    // their own store), but paying is customer-only — switch off the
    // shared admin session (used elsewhere for speed, see global-setup.ts)
    // to the seeded customer account for this flow.
    const loginResponse = await request.post('http://localhost:8000/api/v1/auth/login', {
      data: { email: 'customer@gmail.com', password: 'customer123', tenant_slug: tenantSlug },
    });
    const { access_token } = await loginResponse.json();
    await page.context().addCookies([
      { name: 'token', value: access_token, domain: 'localhost', path: '/' },
      { name: 'tenantSlug', value: tenantSlug, domain: 'localhost', path: '/' },
    ]);

    await page.goto(`/store/${tenantSlug}`);

    // add to cart first — wait for the add to actually land server-side
    // before navigating away, or /checkout can find an empty cart.
    await page.getByRole('button', { name: /add to cart/i }).first().click();
    await expect(page.locator('text=Cart (1)').first()).toBeVisible();

    // go to checkout
    await page.goto('/checkout');

    // fill details
    await page.getByLabel(/name|first name/i).first().fill('John Doe');
    await page.getByLabel(/email/i).first().fill('john@example.com');
    await page.getByLabel(/address/i).first().fill('123 Main St');
    
    // submit
    await page.getByRole('button', { name: /place order|submit/i }).click();

    // Checkout no longer finalizes the order outright — it creates it
    // awaiting a (mock) payment step, which has to be completed too.
    await expect(page.getByTestId('pending-payment')).toBeVisible({ timeout: 10000 });
    await page.getByRole('button', { name: /pay now/i }).click();

    // Verify success
    await expect(page.locator('text=/success|thank you|confirmed/i').first()).toBeVisible({ timeout: 10000 });
  });
});
