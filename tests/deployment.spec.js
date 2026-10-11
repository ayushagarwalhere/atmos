import { test, expect } from '@playwright/test';

test('the public page renders and the smoke twin is usable', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.locator('.preloader')).toHaveCount(0, {timeout: 45000});
  await expect(page.getByRole('link', {name: 'Atmos home', exact: true}).first()).toBeVisible();
  await expect(page.locator('main')).not.toHaveAttribute('inert');
  const scenario = page.getByRole('tab', {name: 'Scenario', exact: true});
  await scenario.scrollIntoViewIfNeeded();
  await scenario.click();
  await expect(scenario).toHaveAttribute('aria-selected', 'true');
  expect(errors).toEqual([]);
  if (process.env.EXPECT_INSECURE_ORIGIN === 'true') {
    expect(await page.evaluate(() => window.isSecureContext)).toBe(false);
  }
});
