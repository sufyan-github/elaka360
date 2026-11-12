import { test } from 'node:test';
import assert from 'node:assert/strict';
import { edgeClientIp } from './edge-ip';

const SECRET = 'x'.repeat(40);
function run(headers: Record<string, string>, secret: string | undefined = SECRET) {
  const req = { headers: { ...headers }, ip: '203.0.113.9' } as unknown as Parameters<ReturnType<typeof edgeClientIp>>[0];
  edgeClientIp(secret)(req, {} as never, () => undefined);
  return req;
}

test('edge IP is used only with the shared secret', () => {
  assert.equal(run({ 'x-edge-key': SECRET, 'x-edge-client-ip': '198.51.100.7' }).ip, '198.51.100.7');
  assert.equal(run({ 'x-edge-key': 'wrong'.repeat(8), 'x-edge-client-ip': '198.51.100.7' }).ip, '203.0.113.9');
  assert.equal(run({ 'x-edge-client-ip': '198.51.100.7' }).ip, '203.0.113.9');
  assert.equal(run({ 'x-edge-key': SECRET, 'x-edge-client-ip': '198.51.100.7' }, '').ip, '203.0.113.9');
  assert.equal(run({ 'x-edge-key': SECRET, 'x-edge-client-ip': 'not an ip' }).ip, '203.0.113.9');
  assert.equal(run({ 'x-edge-key': SECRET }).headers['x-edge-key'], undefined, 'the key is not passed on');
});
