import { test, expect } from '@playwright/test';

test.describe('Storefront & Checkout Flow', () => {
  const tenantSlug = 'test-tenant';
  const productName = `Storefront E2E Product ${Date.now()}`; // Unique name

  test.beforeEach(async ({ page }) => {
    // We need at least one product to test the storefront. Let's create one.
    await page.goto('/admin/login');
    await page.getByLabel(/email/i).fill('admin@test-tenant.com');
    await page.getByLabel(/password/i).fill('admin123');
    await page.getByLabel(/store slug/i).fill(tenantSlug);
    await page.getByRole('button', { name: /log\s*in|sign\s*in/i }).click();
    await page.waitForURL(/\/admin\/(dashboard|products)/);

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

  test('Checkout flow', async ({ page }) => {
    await page.goto(`/store/${tenantSlug}`);
    
    // add to cart first
    await page.getByRole('button', { name: /add to cart/i }).first().click();
    
    // go to checkout
    await page.goto('/checkout');
    
    // fill details
    await page.getByLabel(/name|first name/i).first().fill('John Doe');
    await page.getByLabel(/email/i).first().fill('john@example.com');
    await page.getByLabel(/address/i).first().fill('123 Main St');
    
    // submit
    await page.getByRole('button', { name: /place order|submit/i }).click();
    
    // Verify success
    await expect(page.locator('text=/success|thank you|confirmed/i').first()).toBeVisible({ timeout: 10000 });
  });
});
