import { expect, test, type Page } from '@playwright/test';

/** Signs in through the UI. Needs the API running with SMS_PROVIDER=dev (the code is shown on screen). */
async function signIn(page: Page, phone: string, next = '/me') {
  await page.goto(`/login?next=${encodeURIComponent(next)}`);
  await page.getByLabel('মোবাইল নম্বর').fill(phone);
  await page.getByRole('button', { name: 'কোড পাঠান' }).click();
  const hint = await page.getByText(/ডেভেলপমেন্ট সার্ভার: কোড \d{6}/).textContent();
  const code = /(\d{6})/.exec(hint ?? '')![1]!;
  await page.getByLabel('৬-অঙ্কের কোড').fill(code);
  await page.getByLabel(/আপনার নাম/).fill('E2E ব্যবহারকারী');
  await page.getByRole('button', { name: 'সাইন ইন' }).click();
  await expect(page).toHaveURL(new RegExp(next.replace(/\//g, '\\/')));
}

const phone = () => `0171${String(Date.now()).slice(-7)}`;

test('sign in, save a place, see it in Saved, sign out', async ({ page }) => {
  await signIn(page, phone(), '/p/ruet');
  await page.getByRole('button', { name: 'সংরক্ষণ' }).click();
  await expect(page.getByRole('button', { name: 'সংরক্ষিত' })).toHaveAttribute('aria-pressed', 'true');
  await page.goto('/saved');
  await expect(page.getByRole('link', { name: /রাজশাহী প্রকৌশল/ })).toBeVisible();
  await page.goto('/me');
  await page.getByRole('button', { name: 'সাইন আউট', exact: true }).click();
  await expect(page).toHaveURL(/localhost:3000\/$/);          // sign-out finished and redirected home
  await page.goto('/saved');
  await expect(page).toHaveURL(/\/login/);
});

test('submit a correction through the wizard and track it on the profile', async ({ page }) => {
  await signIn(page, phone(), '/p/puthia-rajbari');
  await page.getByRole('link', { name: /ভুল তথ্য জানান/ }).click();
  await expect(page).toHaveURL(/\/contribute\/new\?type=correction&place=puthia-rajbari/);
  await page.getByRole('button', { name: 'পরের ধাপ' }).click();
  await page.getByLabel('কোন তথ্য?').fill('দূরত্ব');
  await page.getByLabel('সঠিক তথ্য *').fill('রাজশাহী শহর থেকে প্রায় ৩০ কিমি');
  await page.getByRole('button', { name: 'পরের ধাপ' }).click();
  await page.getByRole('button', { name: 'পরের ধাপ' }).click();
  await page.getByLabel(/আমি নিশ্চিত করছি/).check();
  await page.getByRole('button', { name: 'জমা দিন' }).click();
  await expect(page).toHaveURL(/\/me$/);
  await expect(page.getByText('জমা দেওয়া হয়েছে').first()).toBeVisible();
});

test('write a review on a place', async ({ page }) => {
  await signIn(page, phone(), '/p/varendra-research-museum');
  await page.getByRole('button', { name: '৫ তারা' }).click();
  await page.getByLabel(/মন্তব্য/).fill('সুন্দর জাদুঘর');
  await page.getByRole('button', { name: 'রিভিউ জমা দিন' }).click();
  await expect(page.getByText('ধন্যবাদ! আপনার রিভিউ যুক্ত হয়েছে।')).toBeVisible();
});
