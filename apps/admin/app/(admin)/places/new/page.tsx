import type { DataSource } from '@elaka360/shared';
import { createPlace } from '../../actions';
import { PlaceForm } from '@/components/PlaceForm';
import { Card, ErrorPanel, PageHeader } from '@/components/ui';
import { apiTry } from '@/lib/api';
import { categoryOptions } from '@/lib/categories';
import { Forbidden, access } from '@/lib/guard';

export const metadata = { title: 'নতুন স্থান' };

export default async function NewPlacePage() {
  const { ok, can } = await access('places.edit');
  if (!ok) return <Forbidden perm="places.edit" />;
  const [cats, src] = await Promise.all([categoryOptions(), can('sources.read') ? apiTry<{ items: DataSource[] }>('/v1/admin/sources') : Promise.resolve(null)]);
  return (
    <>
      <PageHeader title="নতুন স্থান" en="Create place" back={{ href: '/places', label: 'স্থানের তালিকা' }} />
      {cats.error && <div className="mb-4"><ErrorPanel error={{ detail: cats.error }} title="ক্যাটাগরি আনা যায়নি" /></div>}
      <Card><div className="p-4"><PlaceForm action={createPlace} categories={cats.options} sources={src?.data?.items ?? []} /></div></Card>
    </>
  );
}
