import { formatNumber } from '@elaka360/shared';
import { revokeApiKey } from '../actions';
import { ActionForm, SubmitButton } from '@/components/ActionForm';
import { NewApiKeyForm } from '@/components/NewApiKeyForm';
import { Card, EmptyState, ErrorPanel, PageHeader, formatDateTime } from '@/components/ui';
import { apiTry } from '@/lib/api';
import { Forbidden, access } from '@/lib/guard';

export const metadata = { title: 'ওপেন ডেটা কী' };

interface ApiKeyRow { id: number; name: string; key_prefix: string; rate_per_min: number; created_at: string; last_used_at: string | null; revoked_at: string | null; created_by_name: string | null }

export default async function ApiKeysPage() {
  const { ok } = await access('users.manage');
  if (!ok) return <Forbidden perm="users.manage" />;
  const r = await apiTry<{ items: ApiKeyRow[] }>('/v1/admin/api-keys');
  return (
    <>
      <PageHeader title="ওপেন ডেটা কী" en="Open Data API keys" />
      <p className="mb-4 text-sm text-muted">
        <code className="font-en">/v1/open-data/*</code> শুধু উৎসসহ (production-eligible) তথ্য দেয়, প্রতিটি রেকর্ডে উৎস ও লাইসেন্সের নির্দেশনাসহ।
        কী শুধু তৈরির সময় একবার দেখানো হয়; সার্ভারে শুধু হ্যাশ রাখা হয়।
      </p>
      <Card title="নতুন কী" en="New key"><div className="p-4"><NewApiKeyForm /></div></Card>
      <div className="mt-4">
        {r.error ? <ErrorPanel error={r.error} /> : !r.data.items.length ? <Card><EmptyState title="কোনো কী নেই" /></Card> : (
          <Card>
            <div className="overflow-x-auto">
              <table className="table">
                <thead><tr><th scope="col">নাম</th><th scope="col">কী</th><th scope="col">সীমা/মিনিট</th><th scope="col">তৈরি</th><th scope="col">শেষ ব্যবহার</th><th scope="col">অবস্থা</th><th scope="col"><span className="sr-only">কাজ</span></th></tr></thead>
                <tbody>
                  {r.data.items.map((k) => (
                    <tr key={k.id}>
                      <td>{k.name}<div className="text-xs text-muted">{k.created_by_name ?? ''}</div></td>
                      <td className="font-en">{k.key_prefix}…</td>
                      <td>{formatNumber(k.rate_per_min)}</td>
                      <td>{formatDateTime(k.created_at)}</td>
                      <td>{k.last_used_at ? formatDateTime(k.last_used_at) : '—'}</td>
                      <td>{k.revoked_at ? <span className="text-danger">বাতিল</span> : 'সক্রিয়'}</td>
                      <td>{!k.revoked_at && (
                        <ActionForm action={revokeApiKey.bind(null, k.id)}>
                          <SubmitButton variant="danger" small confirm="এই কী বাতিল করবেন? যারা ব্যবহার করছে তাদের অ্যাক্সেস সঙ্গে সঙ্গে বন্ধ হবে।">বাতিল</SubmitButton>
                        </ActionForm>
                      )}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </>
  );
}
