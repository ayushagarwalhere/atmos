# Mohit Virli theme source

Source: https://github.com/mohitvirli/mohitvirli.github.io
Pinned commit: edc716e10c120f5e19aa8358be433222a83d453e

Original themeStore.ts, ThemeSwitcher.tsx, Stars.tsx and CanvasLoader.tsx are preserved verbatim here. public/icons/night-mode.svg is copied verbatim from the same commit.

Integration: themeStore.ts defaults to the black theme. Stars.tsx uses local imports and pauses animation for reduced motion. ThemeSwitcher replaces Next Image, Tailwind positioning, device detection and portfolio portal visibility with this app's header, an accessible button, native img and a cleaned-up GSAP effect. OpeningJourney uses CanvasLoader's background colors, transition and noise styles, white title text and StarsContainer. The camera far plane is expanded so the original stars are visible. The persisted theme now also drives semantic colors across all page surfaces, text, cards, navigation and controls through src/theme.css.

Window typography, cloud banks and stars: the original `app/components/models/Cloud.tsx`, `WindowModel.tsx`, `Stars.tsx` and `app/components/hero/TextWindow.tsx` are preserved in `reference/` at the same pinned commit. `WindowTypography.jsx` keeps the six mirrored faces and scroll-driven quarter-turn, with Atmos copy and smaller mobile lettering. The window's handle/sash movement remains the original sequence. `OpeningJourney` now uses the original cloud seeds, scales, growth, full white opacity and fade values; its cloud texture matches Drei's upstream texture byte for byte. Both star canvases use the reference's 75-degree camera field of view, and the original 5,000-star settings remain unchanged. The reference's Soria font is hosted locally at `/fonts/soria-font.ttf`.
