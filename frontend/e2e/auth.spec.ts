import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('Login with valid credentials', async ({ page }) => {
    await page.goto('/admin/login');
    
    // Attempt to login using typical generic locators
    await page.getByLabel(/email/i).fill('admin@test-tenant.com');
    await page.getByLabel(/password/i).fill('admin123');
    await page.getByLabel(/store slug/i).fill('test-tenant');
    await page.getByRole('button', { name: /log\s*in|sign\s*in/i }).click();

    // Verify redirection to dashboard or presence of dashboard text
    await expect(page).toHaveURL(/\/admin\/dashboard|\/admin\/categories/);
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible({ timeout: 10000 });
  });

  test('Invalid login shows error toast', async ({ page }) => {
    await page.goto('/admin/login');
    
    await page.getByLabel(/email/i).fill('wrong@example.com');
    await page.getByLabel(/password/i).fill('wrongpassword');
    await page.getByRole('button', { name: /log\s*in|sign\s*in/i }).click();

    // Verify error toast appears
    await expect(page.locator('text=/invalid|error|failed/i').first()).toBeVisible({ timeout: 5000 });
  });
});
