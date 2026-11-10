import { execFileSync } from 'node:child_process';
import { createHmac } from 'node:crypto';
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

function totp(base32: string) {
  const A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = 0, value = 0;
  const bytes: number[] = [];
  for (const ch of base32.replace(/\s/g, '')) {
    value = (value << 5) | A.indexOf(ch);
    bits += 5;
    if (bits >= 8) { bytes.push((value >>> (bits - 8)) & 255); bits -= 8; }
  }
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
  const h = createHmac('sha1', Buffer.from(bytes)).update(counter).digest();
  const o = h[h.length - 1]! & 15;
  return String((((h[o]! & 127) << 24) | (h[o + 1]! << 16) | (h[o + 2]! << 8) | h[o + 3]!) % 1e6).padStart(6, '0');
}

/** When the server requires staff 2FA, enrol through the gate like a real staff member would. */
async function passTwoFactorIfAsked(page: import('@playwright/test').Page) {
  const gate = page.getByRole('heading', { name: 'দুই-ধাপের যাচাই' });
  if (!(await gate.isVisible().catch(() => false))) return false;
  await page.getByRole('button', { name: 'সেটআপ শুরু করুন' }).click();
  const secret = (await page.getByLabel('Secret key').textContent()) ?? '';
  await page.getByLabel(/অথেনটিকেটর কোড/).fill(totp(secret));
  await page.getByRole('button', { name: 'চালু করুন' }).click();
  await expect(page.getByText('রিকভারি কোডগুলো')).toBeVisible();
  await expect(page.locator('li code')).toHaveCount(8);
  await page.getByRole('button', { name: /রেখেছি/ }).click();
  return true;
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
    await page.waitForLoadState('networkidle');
    await passTwoFactorIfAsked(page);
    await expect(page.getByRole('navigation')).toContainText('যাচাই');
    // Live database figures, never mockup numbers: 5,132 non-country areas in the seed, 0 officially verified.
    await expect(page.locator('main')).toContainText('৫,১৩২');
    await expect(page.locator('main')).toContainText('সরকারিভাবে যাচাইকৃত০');
    await page.goto(`${ADMIN}/audit`);
    await expect(page.getByRole('table')).toBeVisible();
    await page.goto(`${ADMIN}/duplicates`);
    await expect(page.getByRole('heading', { name: 'সম্ভাব্য ডুপ্লিকেট' })).toBeVisible();
  });

  test('an administrator issues an Open Data key that is shown once and works', async ({ page, request }) => {
    const phone = `0178${String(Date.now()).slice(-7)}`;
    await adminSignIn(page, phone);
    execFileSync('node', ['apps/api/dist/cli/grant-role.js', phone, 'national_admin'], { env: process.env, stdio: 'pipe' });
    await page.context().clearCookies();
    await adminSignIn(page, phone);
    await page.waitForLoadState('networkidle');
    await passTwoFactorIfAsked(page);
    await page.goto(`${ADMIN}/api-keys`);
    await page.getByLabel(/ব্যবহারকারী\/প্রকল্পের নাম/).fill('E2E consumer');
    await page.getByRole('button', { name: 'কী তৈরি করুন' }).click();
    const key = (await page.getByLabel('API key').textContent())?.trim() ?? '';
    expect(key).toMatch(/^e360_/);
    const api = process.env.API_URL ?? 'http://localhost:4000';
    const res = await request.get(`${api}/v1/open-data/sources`, { headers: { 'X-API-Key': key } });
    expect(res.status()).toBe(200);
    await page.reload();
    await expect(page.getByLabel('API key')).toHaveCount(0);   // never shown again
  });
});
