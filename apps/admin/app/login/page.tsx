import type { Metadata } from 'next';
import { safeNext } from '@/lib/config';
import { LoginForm } from './LoginForm';

export const metadata: Metadata = { title: 'সাইন ইন' };

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const { next } = await searchParams;
  return (
    <main className="flex min-h-dvh items-center justify-center p-4">
      <div className="w-full max-w-sm rounded-card border border-line bg-surface p-6 shadow-card">
        <div className="mb-5">
          <div className="text-xl font-bold text-primary">Elaka360 অ্যাডমিন</div>
          <p className="mt-1 text-sm text-muted">শুধু কর্মীদের জন্য · Staff sign-in</p>
        </div>
        <LoginForm next={safeNext(next)} />
      </div>
    </main>
  );
}
