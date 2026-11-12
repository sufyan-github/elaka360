import { createNavigation } from 'next-intl/navigation';
import { routing } from './routing';

/** Locale-aware Link / router / redirect: hrefs are written without a locale and get `/en` added when needed. */
export const { Link, redirect, usePathname, useRouter, getPathname } = createNavigation(routing);
