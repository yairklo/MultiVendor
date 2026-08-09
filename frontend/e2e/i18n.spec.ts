import { test, expect } from '@playwright/test';

test.describe('Storefront i18n / RTL', () => {
  test('switching to Hebrew toggles dir="rtl" and localized strings without breaking the UI', async ({ page }) => {
    await page.goto('/store/test-tenant');
    await expect(page.getByTestId('product-grid')).toBeVisible();

    // Before switching: LTR, English cart label
    await expect(page.getByText(/^Cart \(\d+\)$/)).toBeVisible();

    await page.getByTestId('language-switcher').click();

    // After switching: RTL direction on the page root, Hebrew cart label
    await expect(page.getByText(/^עגלה \(\d+\)$/)).toBeVisible();
    const dirValue = await page.evaluate(() => {
      const el = document.querySelector('[data-testid="product-grid"]');
      return el?.closest('[dir]')?.getAttribute('dir');
    });
    expect(dirValue).toBe('rtl');

    // UI still functional after switching language
    await expect(page.getByTestId('product-grid')).toBeVisible();
  });
});
