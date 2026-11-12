import type { AuditEntry } from '@elaka360/shared';
import { AuditTable } from '@/components/Audit';
import { Card, ErrorPanel, FilterBar, FilterField, PageHeader, Pager } from '@/components/ui';
import { apiTry, qs } from '@/lib/api';
import { Forbidden, access } from '@/lib/guard';

export const metadata = { title: 'অডিট লগ' };

const ENTITIES = [['admin_area', 'এলাকা'], ['place', 'স্থান'], ['contribution', 'অবদান'], ['data_source', 'উৎস'], ['user', 'ব্যবহারকারী'], ['review', 'রিভিউ']] as const;

type SP = { entity?: string; entity_id?: string; actor_id?: string; cursor?: string };

export default async function AuditPage({ searchParams }: { searchParams: Promise<SP> }) {
  const { ok } = await access('audit.read');
  if (!ok) return <Forbidden perm="audit.read" />;
  const sp = await searchParams;
  const actor = sp.actor_id && /^\d+$/.test(sp.actor_id) ? sp.actor_id : undefined;
  const r = await apiTry<{ items: AuditEntry[]; next_cursor: string | null }>(
    `/v1/admin/audit${qs({ entity: sp.entity, entity_id: sp.entity_id?.trim(), actor_id: actor, cursor: sp.cursor, limit: 50 })}`);
  return (
    <>
      <PageHeader title="অডিট লগ" en="Audit log" />
      <FilterBar action="/audit" resetHref="/audit">
        <FilterField label="রেকর্ডের ধরন" htmlFor="entity">
          <select id="entity" name="entity" defaultValue={sp.entity ?? ''} className="input">
            <option value="">সব</option>
            {ENTITIES.map(([k, l]) => <option key={k} value={k}>{l} ({k})</option>)}
          </select>
        </FilterField>
        <FilterField label="রেকর্ড আইডি" htmlFor="entity_id"><input id="entity_id" name="entity_id" defaultValue={sp.entity_id} className="input font-en" /></FilterField>
        <FilterField label="কর্মীর আইডি" htmlFor="actor_id"><input id="actor_id" name="actor_id" inputMode="numeric" pattern="[0-9]*" defaultValue={sp.actor_id} className="input font-en" /></FilterField>
      </FilterBar>
      <Card>
        {r.error ? <div className="p-4"><ErrorPanel error={r.error} /></div> : (
          <>
            <AuditTable items={r.data.items} empty="এই ফিল্টারে কোনো রেকর্ড নেই" />
            <Pager basePath="/audit" params={sp} nextCursor={r.data.next_cursor} hasCursor={!!sp.cursor} />
          </>
        )}
      </Card>
    </>
  );
}
