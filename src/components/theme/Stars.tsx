
import { useThemeStore } from "../../stores/themeStore";
import { Stars } from "@react-three/drei/core/Stars.js";

const StarsContainer = ({ reduced = false }) => {
  const isDarkTheme = useThemeStore((state) => state.theme.type === 'dark');

  if (!isDarkTheme) return null;

  return (
    <Stars radius={200} depth={100} count={5000} factor={10} saturation={10} fade={true} speed={reduced ? 0 : 1} />
  );
};

export default StarsContainer;