import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Text } from '@react-three/drei/core/Text.js';
import { useTexture } from '@react-three/drei/core/Texture.js';
import * as THREE from 'three';

const FONT = '/fonts/rP2tp2ywxg089UriI5-g4vlH9VoD8CmcqZG40F9JadbnoEwAopxhTg.ttf';
const BUILDINGS = [
  { x: 0.25, height: 0.58, width: 0.36, z: 0 },
  { x: 0.72, height: 1.1, width: 0.43, z: -0.18 },
  { x: 1.25, height: 0.77, width: 0.42, z: 0.08 },
  { x: 1.76, height: 0.48, width: 0.33, z: -0.08 },
];

// An illustrative smoke journey, rather than a simulated live measurement.
export default function SmokeTransportScene({ reduced }) {
  const fire = useRef();
  const arrows = useRef();
  const smokeTexture = useTexture('/textures/cloud.png');
  const flame = useMemo(() => {
    const shape = new THREE.Shape();
    shape.moveTo(0, 0);
    shape.bezierCurveTo(-0.48, 0.1, -0.42, 0.58, -0.15, 0.87);
    shape.bezierCurveTo(-0.12, 0.53, 0.12, 0.64, 0.09, 1.19);
    shape.bezierCurveTo(0.55, 0.77, 0.48, 0.12, 0, 0);
    return shape;
  }, []);

  useFrame(({ clock }) => {
    const time = reduced ? 0 : clock.elapsedTime;
    if (fire.current) fire.current.scale.y = 1 + Math.sin(time * 2.2) * 0.035;
    if (arrows.current) arrows.current.position.x = Math.sin(time * 0.7) * 0.09;
  });

  return <group>
    <mesh position={[0.1, -0.96, -0.15]}>
      <boxGeometry args={[4.45, 0.06, 1.1]}/>
      <meshStandardMaterial color="#68808c" transparent opacity={0.5}/>
    </mesh>
    <group ref={fire} position={[-1.65, -0.92, 0.35]}>
      {[-0.33, 0.25].map((x, index) => <group key={x} position={[x, 0, -index * 0.16]} scale={index ? 0.66 : 0.85}>
        <mesh><shapeGeometry args={[flame]}/><meshBasicMaterial color="#ee9456" side={THREE.DoubleSide}/></mesh>
        <mesh position={[0.01, 0.08, 0.01]} scale={[0.48, 0.53, 1]}>
          <shapeGeometry args={[flame]}/><meshBasicMaterial color="#ffe6af" side={THREE.DoubleSide}/>
        </mesh>
      </group>)}
    </group>
    {/* Soft smoke moves across the skyline along the wind direction. */}
    {[[-1.7,0.04,0.95],[-1.3,0.47,1.05],[-0.65,0.65,1.25],[0.1,0.62,1.35],[0.88,0.48,1.4],[1.6,0.34,1.25]].map(([x,y,scale], index) =>
      <sprite key={x} position={[x,y,0.4]} scale={[scale,scale * 0.65,1]}>
        <spriteMaterial map={smokeTexture} color="#d6dce0" transparent opacity={0.56 - index * 0.045} depthWrite={false}/>
      </sprite>)}
    <group ref={arrows}>
      {[-0.85,0,0.85].map(x => <group key={x} position={[x,1.02,0.5]}>
        <mesh rotation={[0,0,-Math.PI / 2]}><cylinderGeometry args={[0.012,0.012,0.42,8]}/><meshBasicMaterial color="#c9e8f0"/></mesh>
        <mesh position={[0.25,0,0]} rotation={[0,0,-Math.PI / 2]}><coneGeometry args={[0.055,0.13,12]}/><meshBasicMaterial color="#c9e8f0"/></mesh>
      </group>)}
    </group>
    {BUILDINGS.map(({x,height,width,z}) => <group key={x} position={[x,-0.92,z]}>
      <mesh position={[0,height / 2,0]}>
        <boxGeometry args={[width,height,0.38]}/><meshStandardMaterial color="#a9c4d0" roughness={0.75}/>
      </mesh>
      {[0.2,0.43,0.66,0.89].filter(y => y < height - 0.09).map(y => [-0.09,0.09].map(dx =>
        <mesh key={`${dx}-${y}`} position={[dx,y,0.195]}>
          <planeGeometry args={[0.055,0.075]}/><meshBasicMaterial color="#fff4d4"/>
        </mesh>))}
    </group>)}
    <Text font={FONT} fontSize={0.2} color="#ffffff" anchorX="center" position={[-1.62,-1.24,0.55]}>Upwind fires</Text>
    <Text font={FONT} fontSize={0.2} color="#ffffff" anchorX="center" position={[0,1.36,0.55]}>Wind transport</Text>
    <Text font={FONT} fontSize={0.2} color="#ffffff" anchorX="center" position={[1,-1.24,0.55]}>Downwind city</Text>
  </group>;
}
