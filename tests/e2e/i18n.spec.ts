import { expect, test } from '@playwright/test';

/** English lives under /en; Bangla stays at the unprefixed URLs (covered by public.spec.ts). */

test('English home is in English with lang="en"', async ({ page }) => {
  await page.goto('/en');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Information on every area');
  await expect(page.getByRole('link', { name: /Emergency services 999/ })).toBeVisible();
  await expect(page.getByText('nuhil/bangladesh-geocode')).toBeVisible();
  // Links inside the page stay in English.
  await expect(page.getByRole('link', { name: 'See all divisions' })).toHaveAttribute('href', '/en/explore');
});

test('language switch round-trips on an area page, keeping the path', async ({ page }) => {
  await page.goto('/rajshahi/rajshahi');
  await expect(page.locator('html')).toHaveAttribute('lang', 'bn');
  await page.getByRole('link', { name: 'English', exact: true }).click();
  await expect(page).toHaveURL(/\/en\/rajshahi\/rajshahi$/);
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Rajshahi District');
  await page.getByRole('link', { name: 'বাংলা', exact: true }).click();
  await expect(page).toHaveURL(/localhost:3000\/rajshahi\/rajshahi$/);
  await expect(page.locator('html')).toHaveAttribute('lang', 'bn');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('রাজশাহী জেলা');
});

test('language switch keeps the query string', async ({ page }) => {
  await page.goto('/search?q=rajshahi');
  await expect(page.getByRole('link', { name: 'English', exact: true })).toHaveAttribute('href', '/en/search?q=rajshahi');
});

test('English place page shows the English name first and its evidence', async ({ page }) => {
  await page.goto('/en/p/university-of-rajshahi');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('University of Rajshahi');
  await expect(page.getByText('রাজশাহী বিশ্ববিদ্যালয়', { exact: false }).first()).toBeVisible();   // Bangla name underneath
  await expect(page.getByText('Officially verified').first()).toBeVisible();
  await expect(page.getByRole('complementary', { name: 'Source and verification' })).toContainText('Wikipedia');
  await expect(page.getByRole('link', { name: /Report an error/ })).toHaveAttribute('href', /^\/en\/contribute\/new\?type=correction/);
});

test('unverified records carry the "Not verified" warning in English', async ({ page }) => {
  await page.goto('/en/dhaka/dhaka/savar');
  await expect(page.getByRole('note')).toContainText('Not verified.');
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', /noindex/);
});

test('English emergency page lists 999', async ({ page }) => {
  await page.goto('/en/emergency');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.getByRole('link', { name: /Call 999/ })).toHaveAttribute('href', 'tel:999');
  await expect(page.getByText('Important national hotlines')).toBeVisible();
  await expect(page.locator('a[href="tel:999"]').nth(1)).toBeVisible();
});

test('English protected pages redirect to the English sign-in page', async ({ page }) => {
  await page.goto('/en/me');
  await expect(page).toHaveURL(/\/en\/login\?next=%2Fen%2Fme$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Sign in');
  await expect(page.getByLabel('Mobile number')).toBeVisible();
});

test('hreflang alternates and canonical are present', async ({ page }) => {
  await page.goto('/en/p/ruet');
  await expect(page.locator('link[rel="alternate"][hreflang="bn"]')).toHaveAttribute('href', /\/p\/ruet$/);
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveAttribute('href', /\/en\/p\/ruet$/);
  await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveAttribute('href', /\/p\/ruet$/);
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', /\/en\/p\/ruet$/);
  await page.goto('/about');
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveAttribute('href', /\/en\/about$/);
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', /localhost:3000\/about$/);
});

test('English static pages render with English headings', async ({ page }) => {
  for (const [path, heading] of [
    ['/en/about', 'About us'], ['/en/data-policy', 'Data & verification policy'], ['/en/privacy', 'Privacy policy'],
    ['/en/terms', 'Terms of use'], ['/en/guidelines', 'Contribution guidelines'], ['/en/contact', 'Contact'],
  ] as const) {
    const res = await page.goto(path);
    expect(res?.status(), path).toBe(200);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(heading);
  }
});

test('no horizontal overflow on English pages', async ({ page }) => {
  for (const path of ['/en', '/en/rajshahi/rajshahi', '/en/p/ruet', '/en/emergency']) {
    await page.goto(path);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, path).toBeLessThanOrEqual(1);
  }
});
