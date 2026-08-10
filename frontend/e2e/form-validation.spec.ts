import { test, expect } from '@playwright/test';

test.describe('CMS form validation', () => {
  test('submitting an empty product form shows field-level errors and does not navigate away', async ({ page }) => {
    await page.goto('/admin/products/new');

    await page.getByRole('button', { name: /save product/i }).click();

    await expect(page.getByText(/Name must be at least 2 characters/i)).toBeVisible();
    await expect(page.getByText(/must contain at least 2 character/i)).toBeVisible();
    await expect(page).toHaveURL(/\/admin\/products\/new$/);
  });

  test('an invalid slug (uppercase / special characters) is rejected client-side', async ({ page }) => {
    await page.goto('/admin/products/new');

    await page.getByLabel(/Product Name/i).fill('Malformed Slug Product');
    await page.getByLabel(/slug/i).fill('Not A Valid Slug!');
    await page.getByLabel(/price/i).fill('10');
    await page.getByRole('button', { name: /save product/i }).click();

    await expect(page.getByText(/Lowercase alphanumeric and hyphens only/i)).toBeVisible();
    await expect(page).toHaveURL(/\/admin\/products\/new$/);
  });
});
