import { test } from 'node:test';
import assert from 'node:assert/strict';
import { base32Decode, base32Encode, decryptSecret, encryptSecret, totpAt, verifyTotp } from './totp';

// RFC 6238 Appendix B test vector (SHA-1): secret "12345678901234567890", T = 59 s → 94287082 (8 digits) → 287082.
test('TOTP matches the RFC 6238 vector', () => {
  const secret = base32Encode(Buffer.from('12345678901234567890'));
  assert.equal(totpAt(secret, Math.floor(59 / 30)), '287082');
  assert.equal(totpAt(secret, Math.floor(1111111109 / 30)), '081804');
});

test('base32 round-trip', () => {
  const b = Buffer.from([0, 1, 2, 250, 255, 7, 9]);
  assert.deepEqual(base32Decode(base32Encode(b)), b);
});

test('verifyTotp accepts ±1 step and rejects replay', () => {
  const secret = base32Encode(Buffer.from('abcdefghijabcdefghij'));
  const now = 1_800_000_000_000;
  const step = Math.floor(now / 30000);
  assert.equal(verifyTotp(secret, totpAt(secret, step), null, now), step);
  assert.equal(verifyTotp(secret, totpAt(secret, step - 1), null, now), step - 1);
  assert.equal(verifyTotp(secret, totpAt(secret, step - 2), null, now), null);
  assert.equal(verifyTotp(secret, totpAt(secret, step), step, now), null, 'same step cannot be reused');
  assert.equal(verifyTotp(secret, 'abcdef', null, now), null);
});

test('secret encryption round-trip', () => {
  process.env.AUTH_TOTP_KEY = 'x'.repeat(40);
  const s = 'JBSWY3DPEHPK3PXP';
  const enc = encryptSecret(s);
  assert.notEqual(enc, s);
  assert.equal(decryptSecret(enc), s);
});
