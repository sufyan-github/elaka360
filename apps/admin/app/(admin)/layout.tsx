import { Shell } from '@/components/Shell';
import { ErrorPanel } from '@/components/ui';
import { getMeResult } from '@/lib/api';
import { ROLE_LABEL } from '@/lib/labels';
import { NAV, has } from '@/lib/nav';

export const dynamic = 'force-dynamic';

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const r = await getMeResult();
  if (r.error) {
    return <main className="mx-auto max-w-lg p-6"><ErrorPanel error={r.error} title="অ্যাকাউন্টের তথ্য আনা যায়নি" /></main>;
  }
  const me = r.data;
  if (!me.permissions.length) {
    return (
      <main className="flex min-h-dvh items-center justify-center p-4">
        <div role="alert" className="max-w-md rounded-card border border-line bg-surface p-6 text-center shadow-card">
          <h1 className="text-xl font-bold">প্রবেশাধিকার নেই — শুধু কর্মীদের জন্য</h1>
          <p className="font-en mt-1 text-sm text-muted">Access denied — staff only</p>
          <p className="mt-4 text-sm">
            আপনি <strong>{me.name}</strong> হিসেবে সাইন ইন করেছেন ({ROLE_LABEL[me.role]?.bn ?? me.role})। এই অ্যাকাউন্টে অ্যাডমিন অনুমতি নেই।
            প্রয়োজন হলে একজন অ্যাডমিনিস্ট্রেটরকে ভূমিকা দিতে বলুন।
          </p>
          <form method="post" action="/api/auth/logout" className="mt-5">
            <button type="submit" className="btn btn-primary">অন্য অ্যাকাউন্টে সাইন ইন</button>
          </form>
        </div>
      </main>
    );
  }
  const nav = NAV.filter((n) => has(me.permissions, n.perm));
  const role = ROLE_LABEL[me.role] ?? { bn: me.role, en: me.role };
  return (
    <Shell nav={nav} user={{ name: me.name, role: role.bn, roleEn: role.en, scope: me.scope_area_id ? `scope #${me.scope_area_id}` : null }}>
      {children}
    </Shell>
  );
}
