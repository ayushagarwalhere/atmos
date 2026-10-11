import { useCallback, useEffect, useState } from 'react';

export default function useTwinFullscreen(ref) {
  const [expanded, setExpanded] = useState(false);
  const toggle = useCallback(async () => {
    if (expanded) {
      if (document.fullscreenElement) await document.exitFullscreen().catch(() => {});
      setExpanded(false);
      return;
    }
    setExpanded(true);
    try { await ref.current?.requestFullscreen?.(); } catch { /* CSS fallback */ }
  }, [expanded, ref]);
  useEffect(() => {
    const changed = () => { if (!document.fullscreenElement) setExpanded(false); };
    document.addEventListener('fullscreenchange', changed);
    return () => document.removeEventListener('fullscreenchange', changed);
  }, []);
  useEffect(() => {
    if (!expanded || !ref.current) return;
    const previousFocus = document.activeElement, previousOverflow = document.body.style.overflow;
    const ancestors = [];
    for (let parent = ref.current.parentElement; parent && parent !== document.body; parent = parent.parentElement) {
      ancestors.push([parent, parent.style.transform, parent.style.filter]);
      parent.style.transform = 'none'; parent.style.filter = 'none';
    }
    document.body.style.overflow = 'hidden';
    ref.current.querySelector('[data-maximize]')?.focus();
    const keys = event => {
      if (event.key === 'Escape') { setExpanded(false); return; }
      if (event.key !== 'Tab') return;
      const controls = [...ref.current.querySelectorAll('button,a[href],input,select,textarea,[tabindex="0"]')].filter(el => !el.disabled && el.getClientRects().length);
      const first = controls[0], last = controls.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    };
    document.addEventListener('keydown', keys);
    return () => {
      document.body.style.overflow = previousOverflow;
      ancestors.forEach(([parent, transform, filter]) => { parent.style.transform = transform; parent.style.filter = filter; });
      document.removeEventListener('keydown', keys); previousFocus?.focus?.();
    };
  }, [expanded, ref]);
  return [expanded, toggle];
}
