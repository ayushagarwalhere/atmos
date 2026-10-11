import assert from 'node:assert/strict';
import test from 'node:test';
import { createSessionId, persistentSessionId } from '../src/session.js';

const httpCrypto = {getRandomValues: bytes => { bytes.fill(0xab); return bytes; }};
test('session creation works on public HTTP origins without randomUUID', () => {
  assert.equal(createSessionId(httpCrypto), 'abababab-abab-4bab-abab-abababababab');
});
test('stored sessions are reused and newly created sessions are persisted', () => {
  const values = new Map();
  const storage = {getItem:key => values.get(key), setItem:(key,value) => values.set(key,value)};
  const first = persistentSessionId('session', () => storage, httpCrypto);
  assert.equal(values.get('session'), first);
  assert.equal(persistentSessionId('session', () => storage, {randomUUID: () => 'unused'}), first);
});
test('blocked browser storage does not crash the application', () => {
  assert.equal(persistentSessionId('session', () => { throw new Error('Blocked'); }, httpCrypto), createSessionId(httpCrypto));
});
