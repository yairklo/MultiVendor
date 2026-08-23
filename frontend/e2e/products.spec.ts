import { test, expect } from '@playwright/test';

test.describe('Products Management', () => {
  test('Create Product', async ({ page }) => {
    const uniqueId = Date.now();
    const productName = `E2E Test Product ${uniqueId}`;

    await page.goto('/admin/products/new');

    // Fill out form
    await page.getByLabel(/Product Name \(English\)/i).fill(productName);
    await page.getByLabel(/Product Name \(Hebrew\)/i).fill(productName);
    await page.getByLabel(/slug/i).fill(`e2e-test-product-${uniqueId}`);
    await page.getByLabel(/price/i).fill('99.99');
    await page.getByLabel(/Description \(English\)/i).fill('High quality E2E tested product');

    // Category is optional — a real dropdown of the store's categories now,
    // not a raw numeric ID field. Leaving it at "No category" is valid.

    await page.getByRole('button', { name: /save product/i }).click();

    // Verify it appears in the table
    await page.waitForURL(/\/admin\/products$/);
    await expect(page.locator(`text=${productName}`).first()).toBeVisible({ timeout: 5000 });
  });

  test('Subscription Limit Test', async ({ page }) => {
    // Exhausting the real plan quota (hundreds/thousands of products) isn't
    // practical in an E2E test, so simulate the backend's 403 response for
    // this one request to verify the frontend's reaction to it.
    await page.route('**/api/v1/admin/store/*/products', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Maximum number of products reached for this subscription plan' }),
        });
      } else {
        await route.continue();
      }
    });

    await page.goto('/admin/products/new');
    await page.getByLabel(/Product Name \(English\)/i).fill('Limit Test Product');
    await page.getByLabel(/Product Name \(Hebrew\)/i).fill('Limit Test Product');
    await page.getByLabel(/slug/i).fill(`limit-test-product-${Date.now()}`);
    await page.getByLabel(/price/i).fill('1');
    await page.getByRole('button', { name: /save product/i }).click();

    await expect(page.getByTestId('upgrade-prompt')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/reached your plan's product limit/i)).toBeVisible();
    await expect(page.getByRole('link', { name: /upgrade plan/i })).toBeVisible();
  });
});
