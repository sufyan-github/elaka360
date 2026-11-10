import type { Metadata } from 'next';
import { LoginForm } from './LoginForm';

export const metadata: Metadata = { title: 'সাইন ইন', robots: { index: false } };

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const next = (await searchParams).next ?? '/me';
  // Only same-site relative paths are allowed as a post-login destination (no open redirect).
  const safeNext = /^\/(?!\/)[^\s]*$/.test(next) ? next : '/me';
  return (
    <div className="mx-auto max-w-sm pt-8">
      <h1 className="text-2xl font-bold">সাইন ইন</h1>
      <p className="mt-1 text-sm text-muted">আপনার মোবাইল নম্বরে একটি ৬-অঙ্কের কোড পাঠানো হবে। সংরক্ষণ, রিভিউ ও তথ্য যোগ করতে সাইন ইন প্রয়োজন।</p>
      <LoginForm next={safeNext} />
      <p className="mt-6 text-xs text-muted">সাইন ইন করলে আপনি আমাদের ব্যবহারের শর্তাবলি ও গোপনীয়তা নীতি মেনে নিচ্ছেন। আমরা শুধু আপনার ফোন নম্বর ও প্রদর্শিত নাম রাখি।</p>
    </div>
  );
}
