import { test, expect } from '@playwright/test';

test.describe('Categories Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/admin/login');
    await page.getByLabel(/email/i).fill('admin@test-tenant.com');
    await page.getByLabel(/password/i).fill('admin123');
    await page.getByLabel(/store slug/i).fill('test-tenant');
    await page.getByRole('button', { name: /log\s*in|sign\s*in/i }).click();
    await page.waitForURL(/\/admin\/(dashboard|categories)/);
  });

  test('Create Category with real inputs', async ({ page }) => {
    await page.goto('/admin/categories');
    
    // Form is directly on the page
    await page.getByLabel(/name/i).fill('E2E Test Category');
    await page.getByLabel(/slug/i).fill('e2e-test-category');
    await page.getByRole('button', { name: /create category/i }).click();

    // Verify it appears in the data table
    await expect(page.locator('text=E2E Test Category').first()).toBeVisible({ timeout: 5000 });
  });

  test('Empty form validation', async ({ page }) => {
    await page.goto('/admin/categories');
    
    // Submit empty form
    await page.getByRole('button', { name: /create category/i }).click();

    // Verify field-level validation error
    await expect(page.locator('text=/Name must be at least 2 characters/i').first()).toBeVisible();
  });
});
