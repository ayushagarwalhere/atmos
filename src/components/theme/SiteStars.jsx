import { Component, Suspense, useEffect, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { useThemeStore } from '../../stores/themeStore';
import StarsContainer from './Stars';

class StarsBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? null : this.props.children; }
}

export default function SiteStars({ reduced }) {
  const dark = useThemeStore(state => state.theme.type === 'dark');
  const [visible, setVisible] = useState(!document.hidden);
  useEffect(() => {
    const update = () => setVisible(!document.hidden);
    document.addEventListener('visibilitychange', update);
    return () => document.removeEventListener('visibilitychange', update);
  }, []);
  if (!dark) return null;
  return <div className="site-stars" aria-hidden="true">
    <StarsBoundary>
      <Canvas dpr={[1, 1.5]} camera={{ position: [0, 0, 5], fov: 40, far: 1000 }}
        gl={{ alpha: true, antialias: false, powerPreference: 'low-power' }}
        frameloop={reduced || !visible ? 'demand' : 'always'}>
        <Suspense fallback={null}><StarsContainer reduced={reduced} /></Suspense>
      </Canvas>
    </StarsBoundary>
  </div>;
}
