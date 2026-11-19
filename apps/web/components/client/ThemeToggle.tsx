'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Monitor, Moon, Sun } from 'lucide-react';

type Mode = 'system' | 'light' | 'dark';
const NEXT: Record<Mode, Mode> = { system: 'light', light: 'dark', dark: 'system' };

/** Cycles system → light → dark. The choice is applied before paint by the inline script in the locale layout. */
export function ThemeToggle() {
  const t = useTranslations('Theme');
  const [mode, setMode] = useState<Mode>('system');
  useEffect(() => {
    try {
      const m = localStorage.getItem('e360-theme');
      if (m === 'light' || m === 'dark') setMode(m);
    } catch { /* storage blocked */ }
  }, []);
  function cycle() {
    const next = NEXT[mode];
    setMode(next);
    try {
      if (next === 'system') localStorage.removeItem('e360-theme');
      else localStorage.setItem('e360-theme', next);
    } catch { /* storage blocked */ }
    if (next === 'system') document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', next);
  }
  const Icon = mode === 'dark' ? Moon : mode === 'light' ? Sun : Monitor;
  const label = t(mode);
  return (
    <button type="button" onClick={cycle} aria-label={label} title={label} className="grid h-10 w-10 place-items-center rounded-chip border border-line bg-surface">
      <Icon className="h-5 w-5" aria-hidden />
    </button>
  );
}
