import { expect, test } from '@playwright/test';

test('home shows live counts, emergency entry and accurate sources', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('বাংলাদেশের');
  await expect(page.getByRole('link', { name: /জরুরি সেবা ৯৯৯/ })).toBeVisible();   // header, on every screen size
  await expect(page.getByText(/উৎসসহ/).first()).toBeVisible();                   // sourced vs total is disclosed
  await expect(page.getByText('nuhil/bangladesh-geocode')).toBeVisible();
});

test('search finds Rajshahi from Banglish and opens the district', async ({ page }) => {
  await page.goto('/search?q=rajsahi');
  await page.getByRole('link', { name: /^রাজশাহী Rajshahi জেলা/ }).first().click();
  await expect(page).toHaveURL(/\/rajshahi\/rajshahi$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('রাজশাহী জেলা');
  await expect(page.getByText('সরকারিভাবে যাচাইকৃত').first()).toBeVisible();   // BBS 2022 / district portal evidence
});

test('unverified areas are shown with a warning and are not indexed', async ({ page }) => {
  await page.goto('/dhaka/dhaka/savar');
  await expect(page.getByText('কমিউনিটির তথ্য').first()).toBeVisible();          // union cards carry their evidence
  await expect(page.getByRole('note')).toContainText('যাচাই করা হয়নি');
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', /noindex/);
});

test('place page shows evidence, source and report link; unverified places are labelled', async ({ page }) => {
  await page.goto('/p/university-of-rajshahi');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('রাজশাহী বিশ্ববিদ্যালয়');
  await expect(page.getByText('বিশ্ববিদ্যালয়', { exact: true })).toBeVisible();     // Bangla subcategory, not a raw slug
  const footer = page.getByRole('complementary', { name: 'তথ্যের উৎস ও যাচাই' });
  await expect(footer).toContainText('UGC');                // confirmed by the UGC register …
  await expect(footer).toContainText('বিস্তারিত তথ্য: Wikipedia');   // … details still credited to Wikipedia
  await expect(page.getByRole('link', { name: /ভুল তথ্য জানান/ })).toBeVisible();
  await page.goto('/p/shah-makhdum-mazar');
  await expect(page.getByRole('note')).toContainText('যাচাই করা হয়নি');
});

test('live map: Rajshahi District first, division next, boundaries from the API', async ({ page, request }) => {
  await page.goto('/map');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('লাইভ মানচিত্র — রাজশাহী');
  await expect(page.getByRole('button', { name: 'রাজশাহী জেলা' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('button', { name: 'রাজশাহী বিভাগ' })).toBeVisible();
  await expect(page.getByRole('checkbox', { name: 'ইউনিয়নের সীমানা' })).toBeChecked();
  const res = await request.get('/api/boundaries?area_id=20015&levels=upazila,city_corporation');
  expect(res.ok()).toBeTruthy();
  expect((await res.json()).features).toHaveLength(10);
});

test('emergency page lists only sourced hotlines and never the retired fire number', async ({ page }) => {
  await page.goto('/emergency');
  await expect(page.getByRole('link', { name: /৯৯৯-এ কল করুন/ })).toHaveAttribute('href', 'tel:999');
  await expect(page.locator('a[href="tel:102"]').first()).toBeVisible();
  await expect(page.locator('a[href="tel:16163"]')).toHaveCount(0);
  await expect(page.locator('a[href="tel:16263"]')).toHaveCount(0);   // unverified health line is not callable
});

test('category list reports a true total', async ({ page }) => {
  await page.goto('/c/education');
  await expect(page.getByRole('heading', { name: /মোট পাওয়া গেছে/ })).toBeVisible();
});

test('protected pages redirect to sign-in', async ({ page }) => {
  await page.goto('/saved');
  await expect(page).toHaveURL(/\/login\?next=%2Fsaved/);
});

test('static information pages render', async ({ page }) => {
  for (const path of ['/about', '/data-policy', '/privacy', '/terms', '/guidelines', '/contact']) {
    const res = await page.goto(path);
    expect(res?.status(), path).toBe(200);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  }
});

test('no horizontal overflow on key pages', async ({ page }) => {
  for (const path of ['/', '/rajshahi/rajshahi', '/p/ruet', '/emergency', '/search?q=raj']) {
    await page.goto(path);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, path).toBeLessThanOrEqual(1);
  }
});
