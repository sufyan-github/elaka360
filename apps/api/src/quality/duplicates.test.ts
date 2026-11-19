import { test } from 'node:test';
import assert from 'node:assert/strict';
import { BLOCK_THRESHOLD, REVIEW_THRESHOLD, score } from './duplicates';

test('duplicate scores follow the plan thresholds', () => {
  assert.equal(score(1, 0), 100);
  assert.ok(score(1, 0) >= BLOCK_THRESHOLD, 'same name, same spot blocks publication');
  assert.ok(score(0.8, 100) >= REVIEW_THRESHOLD && score(0.8, 100) < BLOCK_THRESHOLD, 'close name nearby goes to review');
  assert.ok(score(0.4, 400) < REVIEW_THRESHOLD, 'weak match is treated as new');
  assert.equal(score(1, null), 90, 'without coordinates a name match is review, never block');
});
