'use client';

import { useState } from 'react';
import type { UserRole } from '@elaka360/shared';
import type { ActionState } from '@/app/(admin)/actions';
import { ROLE_LABEL } from '@/lib/labels';
import type { UserRow } from '@/lib/types';
import { ActionForm, Field, SubmitButton } from './ActionForm';

export function UserEditForm({ action, user, roles }: { action: (prev: ActionState, fd: FormData) => Promise<ActionState>; user: UserRow; roles: UserRole[] }) {
  const p = `u-${user.id}`;
  const [role, setRole] = useState<string>(user.role);
  const [status, setStatus] = useState(user.status);
  const [scope, setScope] = useState(user.scope_area_id ? String(user.scope_area_id) : '');
  const changes: string[] = [];
  if (role !== user.role) changes.push(`ভূমিকা: ${ROLE_LABEL[user.role]?.bn ?? user.role} → ${ROLE_LABEL[role as UserRole]?.bn ?? role}`);
  if (status !== user.status) changes.push(status === 'suspended' ? 'অ্যাকাউন্ট স্থগিত হবে এবং সব সেশন বাতিল হবে' : 'অ্যাকাউন্ট সক্রিয় হবে');
  if (scope !== (user.scope_area_id ? String(user.scope_area_id) : '')) changes.push(`এলাকার পরিধি: ${scope ? `#${scope}` : 'সারা দেশ'}`);
  const roleOptions = roles.includes(user.role) ? roles : [user.role, ...roles];

  return (
    <ActionForm action={action} className="space-y-3" confirm={changes.length ? `${user.name}:\n• ${changes.join('\n• ')}\n\nনিশ্চিত?` : undefined}>
      <input type="hidden" name="orig_role" value={user.role} />
      <input type="hidden" name="orig_status" value={user.status} />
      <input type="hidden" name="orig_scope_area_id" value={user.scope_area_id ?? ''} />
      <div className="grid gap-3 md:grid-cols-3">
        <Field label="ভূমিকা" en="role" htmlFor={`${p}-role`}>
          <select id={`${p}-role`} name="role" className="input" value={role} onChange={(e) => setRole(e.target.value)}>
            {roleOptions.map((r) => <option key={r} value={r} disabled={!roles.includes(r)}>{ROLE_LABEL[r]?.bn ?? r} ({ROLE_LABEL[r]?.en ?? r})</option>)}
          </select>
        </Field>
        <Field label="অবস্থা" en="status" htmlFor={`${p}-status`}>
          <select id={`${p}-status`} name="status" className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="active">সক্রিয় (active)</option>
            <option value="suspended">স্থগিত (suspended)</option>
          </select>
        </Field>
        <Field label="এলাকার পরিধি (আইডি)" en="scope_area_id" htmlFor={`${p}-scope`} hint="খালি = সারা দেশ">
          <input id={`${p}-scope`} name="scope_area_id" inputMode="numeric" pattern="[0-9]*" className="input font-en" value={scope} onChange={(e) => setScope(e.target.value.trim())} aria-describedby={`${p}-scope-hint`} />
        </Field>
      </div>
      <Field label="কারণ" en="reason (required, ≥5)" htmlFor={`${p}-reason`} required>
        <input id={`${p}-reason`} name="reason" className="input" required minLength={5} maxLength={500} />
      </Field>
      <SubmitButton variant={status === 'suspended' && user.status !== 'suspended' ? 'danger' : 'primary'}>সংরক্ষণ</SubmitButton>
    </ActionForm>
  );
}
