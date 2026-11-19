import type { AdminLevel } from '@elaka360/shared';
import { EVIDENCE_LABEL, LEVEL_LABEL } from '@elaka360/shared';
import { EVIDENCE_LEVELS } from '@/lib/labels';

export const AREA_LEVELS: AdminLevel[] = ['division', 'district', 'upazila', 'city_corporation', 'pourashava', 'union', 'ward'];

export function EvidenceSelect({ id = 'evidence', name = 'evidence', value, any = 'সব স্তর' }: { id?: string; name?: string; value?: string; any?: string }) {
  return (
    <select id={id} name={name} defaultValue={value ?? ''} className="input">
      <option value="">{any}</option>
      {EVIDENCE_LEVELS.map((l) => <option key={l} value={l}>{EVIDENCE_LABEL[l].bn} ({EVIDENCE_LABEL[l].en})</option>)}
    </select>
  );
}

export function EligibleSelect({ value }: { value?: string }) {
  return (
    <select id="eligible" name="eligible" defaultValue={value ?? ''} className="input">
      <option value="">সব</option>
      <option value="true">প্রকাশিত (public)</option>
      <option value="false">অপ্রকাশিত (not public)</option>
    </select>
  );
}

export function LevelSelect({ value }: { value?: string }) {
  return (
    <select id="level" name="level" defaultValue={value ?? ''} className="input">
      <option value="">সব স্তর</option>
      {AREA_LEVELS.map((l) => <option key={l} value={l}>{LEVEL_LABEL[l].bn} ({LEVEL_LABEL[l].en})</option>)}
    </select>
  );
}
