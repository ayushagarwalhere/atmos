export function createSessionId(cryptoApi = globalThis.crypto) {
  if (typeof cryptoApi?.randomUUID === 'function') return cryptoApi.randomUUID();
  // getRandomValues is available on HTTP too; randomUUID requires HTTPS.
  const bytes = cryptoApi.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  const hex = [...bytes].map(value => value.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
}

export function persistentSessionId(key, storageProvider = () => globalThis.localStorage, cryptoApi = globalThis.crypto) {
  let storage;
  try {
    storage = storageProvider();
    const existing = storage.getItem(key);
    if (existing) return existing;
  } catch { /* Browsers can disable local storage; keep an in-memory session. */ }
  const id = createSessionId(cryptoApi);
  try { storage?.setItem(key, id); } catch { /* The current session still works. */ }
  return id;
}
