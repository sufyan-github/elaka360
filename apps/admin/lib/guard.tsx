import 'server-only';
import type { Me } from '@elaka360/shared';
import { ShieldAlert } from 'lucide-react';
import { getMe } from './api';
import { has } from './nav';

/** The signed-in user and whether they hold `perm` (the API enforces it again on every call). */
export async function access(perm: string): Promise<{ me: Me; ok: boolean; can: (p: string) => boolean }> {
  const me = await getMe();
  const can = (p: string) => has(me.permissions, p);
  return { me, ok: can(perm), can };
}

export function Forbidden({ perm }: { perm: string }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-card border border-line bg-surface p-6">
      <ShieldAlert className="h-6 w-6 shrink-0 text-danger" aria-hidden />
      <div>
        <h1 className="text-lg font-bold">এই অংশ দেখার অনুমতি আপনার নেই</h1>
        <p className="font-en mt-1 text-sm text-muted">Requires permission <code>{perm}</code>.</p>
      </div>
    </div>
  );
}
