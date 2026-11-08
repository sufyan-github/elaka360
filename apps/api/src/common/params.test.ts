import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cursor, intParam, normalisePath } from './params';

test('cursor round-trip', () => {
  assert.equal(cursor.decode(cursor.encode(40)), 40);
  assert.equal(cursor.decode(undefined), 0);
  assert.throws(() => cursor.decode('bm90LWEtbnVtYmVy'));
});

test('intParam', () => {
  assert.equal(intParam(undefined, 'x', { def: 20 }), 20);
  assert.equal(intParam('5', 'x', { min: 1 }), 5);
  assert.throws(() => intParam('0', 'x', { min: 1 }));
  assert.throws(() => intParam('a', 'x'));
});

test('normalisePath', () => {
  assert.equal(normalisePath('/Rajshahi/rajshahi/'), 'rajshahi/rajshahi');
  assert.equal(normalisePath(''), 'bangladesh');
  assert.throws(() => normalisePath("rajshahi/' or 1=1"));
});
