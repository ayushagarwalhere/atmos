// Adapted from Mohit Virli's ThemeSwitcher.tsx; see vendor/mohitvirli/README.md.
import { useThemeStore } from '../../stores/themeStore';
import gsap from 'gsap';
import { useEffect, useRef } from 'react';

const ThemeSwitcher = () => {
  const themeSwitcherRef = useRef(null);
  const { nextTheme, theme } = useThemeStore();
  const toggleTheme = () => nextTheme();
  useEffect(() => {
    const animation = gsap.to(themeSwitcherRef.current, { opacity: 1, duration: 1, delay: 1 });
    return () => animation.kill();
  }, []);
  useEffect(() => {
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) metaThemeColor.setAttribute('content', theme.color);
  }, [theme.color]);
  return (
    <div className="theme-switcher" ref={themeSwitcherRef} style={{ opacity: 0 }}>
      <button type="button" onClick={toggleTheme} aria-label="Toggle night mode" aria-pressed={theme.type === 'dark'}>
        <img src="/icons/night-mode.svg" width={24} height={24} alt="" loading="lazy" />
      </button>
    </div>
  );
};
export default ThemeSwitcher;
