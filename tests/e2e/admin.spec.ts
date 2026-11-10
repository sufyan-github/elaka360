import { execFileSync } from 'node:child_process';
import { expect, test } from '@playwright/test';

const ADMIN = process.env.ADMIN_URL ?? 'http://localhost:3001';

async function adminSignIn(page: import('@playwright/test').Page, phone: string) {
  await page.goto(`${ADMIN}/login`);
  await page.getByLabel(/মোবাইল/).fill(phone);
  await page.getByRole('button', { name: /কোড পাঠান/ }).click();
  const code = (await page.getByRole('status').locator('strong').textContent())?.trim() ?? '';
  await page.getByLabel(/কোড/).fill(code);
  await page.getByRole('button', { name: /সাইন ইন|প্রবেশ/ }).click();
}

test.describe('admin', () => {
  test.skip(({ isMobile }) => isMobile, 'staff app is desktop/tablet');

  test('non-staff are refused; staff see live dashboard numbers', async ({ page }) => {
    const phone = `0179${String(Date.now()).slice(-7)}`;
    await adminSignIn(page, phone);
    await expect(page.getByText('প্রবেশাধিকার নেই')).toBeVisible();

    execFileSync('node', ['apps/api/dist/cli/grant-role.js', phone, 'data_admin'], { env: process.env, stdio: 'pipe' });
    await page.context().clearCookies();
    await adminSignIn(page, phone);
    await expect(page.getByRole('navigation')).toContainText('যাচাই');
    // Live database figures, never mockup numbers: 5,132 non-country areas in the seed, 0 officially verified.
    await expect(page.locator('main')).toContainText('৫,১৩২');
    await expect(page.locator('main')).toContainText('সরকারিভাবে যাচাইকৃত০');
    await page.goto(`${ADMIN}/audit`);
    await expect(page.getByRole('table')).toBeVisible();
  });
});
