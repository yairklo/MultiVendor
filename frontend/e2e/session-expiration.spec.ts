import { test, expect } from '@playwright/test';

test.describe('Session expiration & unauthorized routing', () => {
  test('accessing /admin/dashboard without a token redirects to /admin/login', async ({ page }) => {
    await page.context().clearCookies();
    await page.goto('/admin/dashboard');
    await expect(page).toHaveURL(/\/admin\/login$/);
  });

  test('accessing /super-admin without a token redirects to /admin/login', async ({ page }) => {
    await page.context().clearCookies();
    await page.goto('/super-admin');
    await expect(page).toHaveURL(/\/admin\/login$/);
  });

  test('an invalid/expired JWT cookie is rejected by the API and the session is cleared', async ({ page }) => {
    await page.context().clearCookies();
    await page.context().addCookies([
      { name: 'token', value: 'this-is-not-a-valid-jwt', url: 'http://localhost:3000' },
    ]);

    await page.goto('/admin/dashboard');
    // The layout guard sees a (bogus) cookie and renders the dashboard shell, which then
    // calls the API, gets a 401, and apiClient redirects to /admin/login.
    await expect(page).toHaveURL(/\/admin\/login$/, { timeout: 10000 });

    const cookies = await page.context().cookies();
    expect(cookies.find(c => c.name === 'token')).toBeUndefined();
  });
});
