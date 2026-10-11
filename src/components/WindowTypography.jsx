import { useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { Text } from '@react-three/drei/core/Text.js';
import * as THREE from 'three';
import { range } from './journeyPath';

// Adapted from Mohit Virli's hero/TextWindow.tsx at edc716e.
// The six faces, mirrored text and quarter-turn follow the upstream window.
export default function WindowTypography({ signal, reduced }) {
  const group = useRef();
  const progress = useRef(0);
  const { size } = useThree();
  const fontScale = size.width < 760 ? 0.65 : 1;
  const fontProps = { font: '/fonts/soria-font.ttf', color: 'white', anchorY: 'middle' };

  useFrame((state, delta) => {
    progress.current = reduced ? signal.current : THREE.MathUtils.damp(progress.current, signal.current, 7, Math.min(delta, 0.05));
    const turn = range(progress.current, 0.65, 0.15);
    if (!group.current) return;
    group.current.rotation.y = -Math.PI / 2 * turn;
    group.current.position.x = -0.6 * turn;
    group.current.position.z = -0.6 * turn;
  });

  return <group position={[0, -0.3, 0]} ref={group}>
    <Text {...fontProps} anchorX="left" fontSize={1.3 * fontScale}
      position={[0.12, 0, 0]} scale={[1, -1, 1]} rotation={[0, 0, -Math.PI / 2]}>
      SMOKE TRAVELS
    </Text>
    <Text {...fontProps} anchorX="right" fontSize={1.3 * fontScale}
      position={[0.12, 0, -1.4]} scale={[-1, -1, 1]} rotation={[0, 0, -Math.PI / 2]}>
      KNOW WHAT ARRIVES
    </Text>
    <group position={[-0.45, 0, -0.3]}>
      <Text {...fontProps} anchorX="left" fontSize={0.8 * fontScale}
        scale={[1, -1, 1]} rotation={[0, -Math.PI / 2, -Math.PI / 2]}>
        FIRE SIGNALS
      </Text>
      <Text {...fontProps} anchorX="left" fontSize={0.8 * fontScale}
        position={[0, 0, -0.6]} scale={[1, -1, 1]} rotation={[0, -Math.PI / 2, -Math.PI / 2]}>
        WIND TRANSPORT
      </Text>
    </group>
    <group position={[0.45, 0, -0.3]}>
      <Text {...fontProps} anchorX="right" fontSize={0.8 * fontScale}
        scale={[-1, -1, 1]} rotation={[0, -Math.PI / 2, -Math.PI / 2]}>
        CITY OUTLOOKS
      </Text>
      <Text {...fontProps} anchorX="right" fontSize={0.8 * fontScale}
        position={[0, 0, -0.6]} scale={[-1, -1, 1]} rotation={[0, -Math.PI / 2, -Math.PI / 2]}>
        CLEARER SKIES
      </Text>
    </group>
  </group>;
}
