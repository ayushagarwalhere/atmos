export const clamp01 = value => Math.max(0, Math.min(1, value));
export const range = (progress, start, length) => clamp01((progress - start) / length);
export const smoothRange = (progress, start, length) => { const t = range(progress, start, length); return t * t * (3 - 2 * t); };
// Mohit Virli's downward camera journey, followed by an Atmos reveal.
export function sampleJourney(progress) {
  const p = clamp01(progress);
  const emergence = smoothRange(p, 0.68, 0.17);
  return {
    x: 0,
    y: p <= 0.68 ? -37 * range(p, 0.3, 0.5) : -28.12 - 3.38 * emergence,
    z: 5 + 4 * emergence,
    pitch: p <= 0.68 ? -Math.PI / 2 * range(p, 0, 0.3) : -Math.PI / 2 * (1 - emergence),
    handle: -Math.PI / 2 * range(p, 0.4, 0.1),
    sash: Math.PI / 2 * range(p, 0.5, 0.1),
    podVisible: p >= 0.79,
  };
}
export function journeyPhase(progress) {
  return progress < 0.22 ? 'sky' : progress < 0.48 ? 'clouds' : progress < 0.64 ? 'window' : progress < 0.8 ? 'emerge' : 'pod';
}
