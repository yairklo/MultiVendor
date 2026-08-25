import { test, expect } from '@playwright/test';

test.describe('Storefront i18n / RTL', () => {
  test('switching to Hebrew toggles dir="rtl" and localized strings without breaking the UI', async ({ page }) => {
    await page.goto('/store/test-tenant/shop');
    await expect(page.getByTestId('product-grid')).toBeVisible();

    const cartEn = page.getByText(/^Cart \(\d+\)$/);
    const cartHe = page.getByText(/^עגלה \(\d+\)$/);
    const switcher = page.getByTestId('language-switcher');

    await expect(switcher).toBeVisible();
    await expect(cartEn.or(cartHe)).toBeVisible();
    await switcher.selectOption('en');
    await expect(cartEn).toBeVisible();

    await switcher.selectOption('he');

    await expect(cartHe).toBeVisible();
    const dirValue = await page.evaluate(() => {
      const el = document.querySelector('[data-testid="product-grid"]');
      return el?.closest('[dir]')?.getAttribute('dir') ?? document.documentElement.getAttribute('dir');
    });
    expect(dirValue).toBe('rtl');

    await expect(page.getByTestId('product-grid')).toBeVisible();
  });
});
