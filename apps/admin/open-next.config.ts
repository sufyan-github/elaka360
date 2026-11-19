import { defineCloudflareConfig } from '@opennextjs/cloudflare';

// Every admin page is dynamic (per-user, no-store): no incremental cache needed.
export default defineCloudflareConfig({});
