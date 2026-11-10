'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Bookmark, BookmarkCheck, Share2 } from 'lucide-react';

/** Save (needs sign-in; state loaded in the browser so the page itself stays cacheable) and share. */
export function SaveShare({ placeSlug, areaPath, title }: { placeSlug?: string; areaPath?: string; title: string }) {
  const router = useRouter();
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const here = placeSlug ? `/p/${placeSlug}` : `/${areaPath}`;

  useEffect(() => {
    const ctrl = new AbortController();
    fetch('/api/u/me/saved', { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((d: { items: { place: { slug: string } | null; area: { path: string } | null }[] } | null) => {
        if (d) setSaved(d.items.some((i) => (placeSlug ? i.place?.slug === placeSlug : i.area?.path === areaPath)));
      })
      .catch(() => undefined);
    return () => ctrl.abort();
  }, [placeSlug, areaPath]);

  async function toggle() {
    setBusy(true);
    setMsg(null);
    const target: Record<string, string> = placeSlug ? { place_slug: placeSlug } : { area_path: areaPath ?? '' };
    const res = saved
      ? await fetch(`/api/u/me/saved?${new URLSearchParams(target)}`, { method: 'DELETE' })
      : await fetch('/api/u/me/saved', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(target) });
    setBusy(false);
    if (res.status === 401) return router.push(`/login?next=${encodeURIComponent(here)}`);
    if (res.ok) setSaved(!saved);
    else setMsg('সংরক্ষণ করা যায়নি। আবার চেষ্টা করুন।');
  }

  async function share() {
    const url = window.location.href;
    try {
      if (navigator.share) await navigator.share({ title, url });
      else {
        await navigator.clipboard.writeText(url);
        setMsg('লিংক কপি হয়েছে');
      }
    } catch {
      /* user cancelled */
    }
  }

  const btn = 'flex flex-col items-center gap-1 rounded-chip border border-line py-2 text-sm font-medium';
  return (
    <>
      <button type="button" onClick={toggle} disabled={busy} aria-pressed={saved} className={btn}>
        {saved ? <BookmarkCheck className="h-5 w-5 text-secondary" aria-hidden /> : <Bookmark className="h-5 w-5" aria-hidden />}
        {saved ? 'সংরক্ষিত' : 'সংরক্ষণ'}
      </button>
      <button type="button" onClick={share} className={btn}>
        <Share2 className="h-5 w-5" aria-hidden /> শেয়ার
      </button>
      {msg && <p role="status" className="col-span-full text-center text-xs text-muted">{msg}</p>}
    </>
  );
}
