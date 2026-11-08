import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  toBnDigits, fromBnDigits, groupIndian, formatNumber, formatCompact, formatCount,
  formatArea, formatDistance, formatDate,
} from './bangla';
import { latinKey, aliasesFor } from './search';
import { titleOf, nameOf } from './labels';

test('digits round-trip', () => {
  assert.equal(toBnDigits('2026-11-09'), '২০২৬-১১-০৯');
  assert.equal(fromBnDigits('৯৯৯'), '999');
});

test('indian grouping', () => {
  assert.equal(groupIndian('123'), '123');
  assert.equal(groupIndian('1234'), '1,234');
  assert.equal(groupIndian('2915009'), '29,15,009');
  assert.equal(groupIndian('169828911'), '16,98,28,911');
});

test('formatNumber', () => {
  assert.equal(formatNumber(2915009), '২৯,১৫,০০৯');
  assert.equal(formatNumber(2915009, 'en'), '2,915,009');
  assert.equal(formatNumber(2425.37, 'bn', 2), '২,৪২৫.৩৭');
  assert.equal(formatNumber(-1500, 'en'), '-1,500');
});

test('formatCompact (lakh/crore)', () => {
  assert.equal(formatCompact(2915009), '২৯.১৫ লাখ');
  assert.equal(formatCompact(45644586, 'bn', 1), '৪.৬ কোটি');
  assert.equal(formatCompact(2915009, 'en'), '2.92M');
  assert.equal(formatCompact(950), '৯৫০');
});

test('counts, area, distance, date', () => {
  assert.equal(formatCount(9), '৯টি');
  assert.equal(formatArea(2425.37), '২,৪২৫.৩৭ বর্গ কিমি');
  assert.equal(formatArea(96.72, 'en'), '96.72 km²');
  assert.equal(formatDistance(300), '৩০০ মিটার');
  assert.equal(formatDistance(2100), '২.১ কিমি');
  assert.equal(formatDate('2026-11-09'), '৯ নভেম্বর ২০২৬');
  assert.equal(formatDate('2026-03-15T10:00:00Z', 'en'), '15 Mar 2026');
});

test('search keys', () => {
  assert.equal(latinKey('Rajshahi'), latinKey('Rajsahi'));
  assert.equal(latinKey("Cox's Bazar"), latinKey('Coxs Bazar'));
  assert.ok(aliasesFor('Chapai Nawabganj').includes('chapainawabganj'));
});

test('titles', () => {
  assert.equal(titleOf({ name_bn: 'রাজশাহী', name_en: 'Rajshahi', level: 'district' }, 'bn'), 'রাজশাহী জেলা');
  assert.equal(titleOf({ name_bn: 'রাজশাহী সিটি কর্পোরেশন', name_en: 'Rajshahi City Corporation', level: 'city_corporation' }, 'en'), 'Rajshahi City Corporation');
  assert.equal(nameOf({ name_bn: '', name_en: 'Paba' }, 'bn'), 'Paba');
});
