import { defineConfig, devices } from '@playwright/test';

/**
 * End-to-end tests against running servers (web on :3000, API on :4000 with SMS_PROVIDER=dev).
 * CI starts them before `pnpm e2e`; locally: pnpm --filter @elaka360/web start & the API.
 */
export default defineConfig({
  testDir: 'tests/e2e',
  timeout: 45_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.WEB_URL ?? 'http://localhost:3000',
    locale: 'bn-BD',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 900 } } },
  ],
});
