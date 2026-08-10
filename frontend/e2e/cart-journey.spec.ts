import { test, expect } from '@playwright/test';

test.describe('Storefront Cart Journey', () => {
  const tenantSlug = 'test-tenant';
  const productName = `Cart Journey Product ${Date.now()}`;

  test.beforeEach(async ({ page }) => {
    // Seed a product to shop for via the admin CMS.
    await page.goto('/admin/products/new');
    await page.getByLabel(/Product Name/i).fill(productName);
    await page.getByLabel(/slug/i).fill(`cart-journey-${Date.now()}`);
    await page.getByLabel(/price/i).fill('25.00');
    await page.getByRole('button', { name: /save product/i }).click();
    await page.waitForURL(/\/admin\/products$/);

    await page.goto(`/store/${tenantSlug}`);
  });

  test('add to cart, adjust quantity, remove item, and proceed to checkout', async ({ page }) => {
    await expect(page.getByText(productName)).toBeVisible();

    // Scope to this specific product's card — the storefront may still list
    // products created by earlier test runs, so ".first()" isn't safe here.
    const productCard = page.locator('[data-testid="product-grid"] > div').filter({ hasText: productName });
    await productCard.getByRole('button', { name: /add to cart/i }).click();

    // The cart icon in the header opens a drawer with the added item's details.
    await page.getByTestId('cart-icon').click();
    const drawer = page.getByTestId('cart-drawer');
    await expect(drawer).toBeVisible();

    const item = drawer.getByTestId('cart-item').first();
    await expect(item).toBeVisible();
    await expect(item).toContainText(productName);
    await expect(item).toContainText('25');
    await expect(item.getByRole('img')).toBeVisible();

    // Increment quantity: 1 -> 2, subtotal updates.
    await item.getByRole('button', { name: /increase quantity/i }).click();
    await expect(item).toContainText('2');
    await expect(drawer.getByTestId('cart-subtotal')).toContainText('50');

    // Decrement quantity: 2 -> 1, subtotal updates back.
    await item.getByRole('button', { name: /decrease quantity/i }).click();
    await expect(item).toContainText('1');
    await expect(drawer.getByTestId('cart-subtotal')).toContainText('25');

    // Remove the item entirely.
    await item.getByRole('button', { name: /remove/i }).click();
    await expect(drawer.getByTestId('cart-item')).toHaveCount(0);

    // Add it back so we can proceed to checkout with a populated cart.
    await drawer.getByRole('button', { name: /close/i }).click();
    await productCard.getByRole('button', { name: /add to cart/i }).click();
    await page.getByTestId('cart-icon').click();
    await expect(page.getByTestId('cart-drawer').getByTestId('cart-item')).toHaveCount(1);

    await page.getByRole('button', { name: /proceed to checkout/i }).click();
    await page.waitForURL(/\/checkout$/);
    await expect(page.getByTestId('item-summary')).toContainText(productName);
  });
});
