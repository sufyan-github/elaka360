import type { routing } from '@/i18n/routing';
import type messages from './messages/bn.json';

// Type-checked message keys (bn.json is the source of truth; en.json must have the same keys).
declare module 'next-intl' {
  interface AppConfig {
    Locale: (typeof routing.locales)[number];
    Messages: typeof messages;
  }
}
