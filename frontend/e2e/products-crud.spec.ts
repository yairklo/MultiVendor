import { test, expect, Page } from '@playwright/test';

async function createProduct(page: Page, name: string) {
  await page.goto('/admin/products/new');
  await page.getByLabel(/Product Name \(English\)/i).fill(name);
  await page.getByLabel(/Product Name \(Hebrew\)/i).fill(name);
  await page.getByLabel(/slug/i).fill(`crud-product-${Date.now()}-${Math.floor(Math.random() * 10000)}`);
  await page.getByLabel(/price/i).fill('40.00');
  await page.getByRole('button', { name: /save product/i }).click();
  await page.waitForURL(/\/admin\/products$/);
}

test.describe('Product Edit (CMS CRUD)', () => {
  test('editing a product opens a prefilled form, persists the change, and reflects it in the table', async ({ page }) => {
    const originalName = `CRUD Edit Product ${Date.now()}`;
    const updatedName = `${originalName} (Updated)`;

    await createProduct(page, originalName);

    const row = page.locator('tr', { hasText: originalName });
    await expect(row).toBeVisible();
    await row.getByRole('link', { name: /edit/i }).click();

    await page.waitForURL(/\/admin\/products\/\d+\/edit$/);

    const nameInput = page.getByLabel(/Product Name \(English\)/i);
    await expect(nameInput).toHaveValue(originalName);
    await expect(page.getByLabel(/price/i)).toHaveValue('40');

    await nameInput.fill(updatedName);
    await page.getByLabel(/Product Name \(Hebrew\)/i).fill(updatedName);
    await page.getByRole('button', { name: /save product/i }).click();

    await page.waitForURL(/\/admin\/products$/);
    await expect(page.getByText(updatedName, { exact: true })).toBeVisible();
    await expect(page.getByText(originalName, { exact: true })).not.toBeVisible();
  });

  test('deleting a product actually removes it from the table after a refresh', async ({ page }) => {
    const productName = `CRUD Delete Product ${Date.now()}`;

    await createProduct(page, productName);

    const row = page.locator('tr', { hasText: productName });
    await expect(row).toHaveCount(1);
    await row.getByRole('button', { name: /delete/i }).click();

    // Deletion goes through the app's own confirm dialog, not a native
    // browser confirm() — accept it there instead of via page.on('dialog').
    await page.getByRole('dialog').getByRole('button', { name: /^delete$/i }).click();

    await expect(page.locator('tr', { hasText: productName })).toHaveCount(0);

    await page.reload();
    await expect(page.locator('tr', { hasText: productName })).toHaveCount(0);
  });
});
