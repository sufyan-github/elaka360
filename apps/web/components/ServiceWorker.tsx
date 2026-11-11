'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { RefreshCw, WifiOff, X } from 'lucide-react';

/**
 * Registers /sw.js (production builds only) and shows two small banners:
 *  - a new version is waiting → "refresh" sends SKIP_WAITING, then the page reloads once the new worker takes over;
 *  - the browser is offline, or this page was answered from the service-worker cache → data may be outdated.
 * Render once, in the locale layout.
 */
export function ServiceWorker() {
  const t = useTranslations('ServiceWorker');
  const [waiting, setWaiting] = useState<ServiceWorker | null>(null);
  const [updateDismissed, setUpdateDismissed] = useState(false);
  const [offline, setOffline] = useState(false);
  const [fromCache, setFromCache] = useState(false);
  const [staleDismissed, setStaleDismissed] = useState(false);
  const reloading = useRef(false);

  // Connectivity
  useEffect(() => {
    const update = () => {
      setOffline(!navigator.onLine);
      setStaleDismissed(false);
    };
    update();
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);

  // Registration + update detection
  useEffect(() => {
    if (process.env.NODE_ENV !== 'production' || !('serviceWorker' in navigator)) return;
    const sw = navigator.serviceWorker;
    let reg: ServiceWorkerRegistration | undefined;

    const track = (worker: ServiceWorker | null) => {
      if (!worker) return;
      const check = () => {
        // Only an *update* needs the banner; on first install there is no controller yet.
        if (worker.state === 'installed' && sw.controller) {
          setWaiting(worker);
          setUpdateDismissed(false);
        }
      };
      check();
      worker.addEventListener('statechange', check);
    };

    const onMessage = (e: MessageEvent) => {
      if (e.data?.type === 'PAGE_SOURCE') setFromCache(Boolean(e.data.fromCache));
    };
    const onControllerChange = () => {
      if (!reloading.current) return; // first install claims the page: nothing to reload
      window.location.reload();
    };
    const onVisible = () => {
      if (document.visibilityState === 'visible') reg?.update().catch(() => undefined);
    };

    sw.addEventListener('message', onMessage);
    sw.addEventListener('controllerchange', onControllerChange);
    document.addEventListener('visibilitychange', onVisible);

    sw.register('/sw.js', { scope: '/' })
      .then((r) => {
        reg = r;
        if (r.waiting) track(r.waiting);
        r.addEventListener('updatefound', () => track(r.installing));
      })
      .catch(() => undefined);
    // Ask the worker whether this page came from its cache (it only answers for the controlling worker).
    sw.controller?.postMessage({ type: 'GET_PAGE_SOURCE' });

    return () => {
      sw.removeEventListener('message', onMessage);
      sw.removeEventListener('controllerchange', onControllerChange);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, []);

  const applyUpdate = () => {
    if (!waiting) return;
    reloading.current = true;
    waiting.postMessage({ type: 'SKIP_WAITING' });
  };

  const showUpdate = waiting !== null && !updateDismissed;
  const showStale = (offline || fromCache) && !staleDismissed;
  if (!showUpdate && !showStale) return null;

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-[calc(4.5rem+env(safe-area-inset-bottom))] z-40 flex flex-col items-center gap-2 px-4 md:bottom-4">
      {showStale && (
        <Banner closeLabel={t('close')} onDismiss={() => setStaleDismissed(true)} icon={<WifiOff className="h-5 w-5 shrink-0 text-danger" aria-hidden />}>
          {offline ? t('offline') : t('slow')}
          {!offline && (
            <button type="button" onClick={() => window.location.reload()} className="ml-1 font-semibold text-primary underline underline-offset-2">
              {t('reload')}
            </button>
          )}
        </Banner>
      )}
      {showUpdate && (
        <Banner closeLabel={t('close')} onDismiss={() => setUpdateDismissed(true)} icon={<RefreshCw className="h-5 w-5 shrink-0 text-primary" aria-hidden />}>
          <span>{t('update')}</span>
          <button type="button" onClick={applyUpdate} className="ml-2 rounded-chip bg-primary px-3 py-1.5 text-sm font-semibold text-on-primary hover:bg-primary-hover">
            {t('refresh')}
          </button>
        </Banner>
      )}
    </div>
  );
}

function Banner({ children, icon, onDismiss, closeLabel }: { children: React.ReactNode; icon: React.ReactNode; onDismiss: () => void; closeLabel: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-auto flex w-full max-w-md items-center gap-2 rounded-card border border-line bg-surface px-3 py-2 text-sm text-ink shadow-card transition duration-300 ease-out starting:translate-y-2 starting:opacity-0 motion-reduce:transition-none"
    >
      {icon}
      <div className="min-w-0 flex-1">{children}</div>
      <button type="button" onClick={onDismiss} className="grid h-8 w-8 shrink-0 place-items-center rounded-chip text-muted hover:text-ink" aria-label={closeLabel}>
        <X className="h-4 w-4" aria-hidden />
      </button>
    </div>
  );
}
