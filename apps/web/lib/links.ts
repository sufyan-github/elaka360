/** URL helpers safe to use in both server and client components. */

/** URL of an area page in the web app. The country lives at /explore. */
export function areaHref(a: { path: string; level: string }): string {
  return a.level === 'country' ? '/explore' : `/${a.path}`;
}
