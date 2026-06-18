import { expect, test } from '@playwright/test';

test('loads the Croo shell', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Croo Digital Experience/);
  await expect(page.locator('croo-root')).toBeVisible();
});
