import { test } from 'node:test';
import assert from 'node:assert/strict';
import { confidenceOf, recordStatus } from './trust';

const base = { evidence_level: 'official' as const, lat: 24.37, address_bn: 'রাজশাহী', address_en: null, phones: ['0721-750041'], email: null,
               website: null, subcategory_key: 'education.university', attributes: {}, last_verified_at: null };

test('record status: closure and review come before evidence', () => {
  assert.equal(recordStatus({ evidence_level: 'official', verification_status: 'unverified' }), 'officially_verified');
  assert.equal(recordStatus({ evidence_level: 'secondary', verification_status: 'unverified' }), 'source_verified');
  assert.equal(recordStatus({ evidence_level: 'community', verification_status: 'unverified' }), 'unverified');
  assert.equal(recordStatus({ evidence_level: 'official', verification_status: 'disputed' }), 'needs_review');
  assert.equal(recordStatus({ evidence_level: 'community', verification_status: 'verified' }), 'field_verified');
  assert.equal(recordStatus({ evidence_level: 'official', verification_status: 'verified', status: 'closed' }), 'inactive_closed');
  assert.equal(recordStatus({ evidence_level: 'official', verification_status: 'verified', status: 'archived' }), 'archived');
});

test('confidence adds up its parts and never reaches 100 without a field check', () => {
  const c = confidenceOf(base, new Date('2026-11-19'));
  assert.equal(c.score, 40 + 0 + 20 + 20 + 0);
  assert.equal(c.score, c.parts.reduce((s, p) => s + p.points, 0));
  assert.equal(confidenceOf({ ...base, last_verified_at: '2026-06-01', attributes: { _sources: ['A', 'B', 'C'] } }, new Date('2026-11-19')).score, 100);
  const weak = confidenceOf({ ...base, evidence_level: 'community', lat: null, address_bn: null, phones: [], subcategory_key: null,
                              attributes: { _name_bn_missing: true } });
  assert.equal(weak.score, 12);
});
