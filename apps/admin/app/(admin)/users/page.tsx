import { formatNumber, formatDate } from '@elaka360/shared';
import { updateUser } from '../actions';
import { UserEditForm } from '@/components/UserEditForm';
import { Card, Chip, EmptyState, ErrorPanel, FilterBar, FilterField, PageHeader, Pager, StatusChip, TableWrap, formatDateTime } from '@/components/ui';
import { apiTry, qs } from '@/lib/api';
import { Forbidden, access } from '@/lib/guard';
import { ROLES, ROLE_LABEL, assignableRoles } from '@/lib/labels';
import type { Page, UserRow } from '@/lib/types';

export const metadata = { title: 'ব্যবহারকারী' };

type SP = { q?: string; role?: string; cursor?: string };

export default async function UsersPage({ searchParams }: { searchParams: Promise<SP> }) {
  const { ok, me } = await access('users.manage');
  if (!ok) return <Forbidden perm="users.manage" />;
  const sp = await searchParams;
  const r = await apiTry<Page<UserRow>>(`/v1/admin/users${qs({ q: sp.q, role: sp.role, cursor: sp.cursor, limit: 50 })}`);
  const assignable = assignableRoles(me.role);
  return (
    <>
      <PageHeader title="ব্যবহারকারী" en="Users">{r.data && <span className="text-sm text-muted">মোট {formatNumber(r.data.total)} জন</span>}</PageHeader>
      <FilterBar action="/users" resetHref="/users">
        <FilterField label="নাম বা ফোন" htmlFor="q" wide><input id="q" name="q" type="search" defaultValue={sp.q} className="input" /></FilterField>
        <FilterField label="ভূমিকা" htmlFor="role">
          <select id="role" name="role" defaultValue={sp.role ?? ''} className="input">
            <option value="">সব</option>
            {ROLES.map((x) => <option key={x} value={x}>{ROLE_LABEL[x].bn} ({ROLE_LABEL[x].en})</option>)}
          </select>
        </FilterField>
      </FilterBar>
      <Card>
        {r.error ? <div className="p-4"><ErrorPanel error={r.error} /></div> : !r.data.items.length ? <EmptyState title="কোনো ব্যবহারকারী পাওয়া যায়নি" /> : (
          <>
            <TableWrap>
              <table className="table">
                <thead><tr><th scope="col">নাম</th><th scope="col">ফোন / ইমেইল</th><th scope="col">ভূমিকা</th><th scope="col">পরিধি</th><th scope="col">অবস্থা</th><th scope="col">শেষ লগইন</th><th scope="col"><span className="sr-only">পরিবর্তন</span></th></tr></thead>
                <tbody>
                  {r.data.items.map((u) => {
                    const self = u.id === me.id;
                    const manageable = assignable.includes(u.role) && !self;
                    return (
                      <tr key={u.id}>
                        <td>
                          <div className="font-medium">{u.name}{self && <span className="ml-1 text-xs text-muted">(আপনি)</span>}</div>
                          <div className="font-en text-xs text-muted">#{u.id} · যোগদান {formatDate(u.created_at)}{u.deletion_requested_at ? ' · মুছে ফেলার অনুরোধ' : ''}</div>
                        </td>
                        <td className="font-en text-xs">{u.phone ?? '—'}{u.email && <div>{u.email}</div>}</td>
                        <td><Chip tone={['user', 'contributor'].includes(u.role) ? 'line' : 'tint'}>{ROLE_LABEL[u.role]?.bn ?? u.role}</Chip></td>
                        <td className="font-en text-xs">{u.scope_path ?? (u.scope_area_id ? `#${u.scope_area_id}` : 'সারা দেশ')}</td>
                        <td><StatusChip status={u.status} /></td>
                        <td className="whitespace-nowrap text-xs">{formatDateTime(u.last_login_at)}</td>
                        <td className="min-w-[7rem]">
                          {manageable ? (
                            <details>
                              <summary className="btn btn-outline btn-sm cursor-pointer list-none">পরিবর্তন</summary>
                              <div className="mt-3 w-[min(40rem,80vw)]"><UserEditForm action={updateUser.bind(null, u.id)} user={u} roles={assignable} /></div>
                            </details>
                          ) : <span className="text-xs text-muted">{self ? 'নিজের ভূমিকা বদলানো যায় না' : 'আপনার অনুমতির বাইরে'}</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </TableWrap>
            <Pager basePath="/users" params={sp} nextCursor={r.data.next_cursor} hasCursor={!!sp.cursor} />
          </>
        )}
      </Card>
    </>
  );
}
