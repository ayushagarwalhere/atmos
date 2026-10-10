import { Component, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Center } from '@react-three/drei/core/Center.js';
import { Float } from '@react-three/drei/core/Float.js';
import { RoundedBox } from '@react-three/drei/core/RoundedBox.js';
import { useGLTF } from '@react-three/drei/core/Gltf.js';
import * as THREE from 'three';

useGLTF.setDecoderPath('/draco/');

class SceneBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error) { console.error('Atmos scene:', error); this.props.onReady?.(); }
  render() { return this.state.failed ? <div className="scene-fallback"><div className="fallback-pod"><span /><i /><b /></div></div> : this.props.children; }
}

function useSceneVisibility() {
  const ref=useRef(); const [visible,setVisible]=useState(false);
  useEffect(()=>{const observer=new IntersectionObserver(([entry])=>setVisible(entry.isIntersecting),{rootMargin:'100px'});if(ref.current)observer.observe(ref.current);return()=>observer.disconnect();},[]);
  return [ref,visible];
}
function Ready({ onReady }) {
  useEffect(() => { onReady?.(); }, [onReady]);
  return null;
}

function makeCloudTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 128;
  const ctx = canvas.getContext('2d');
  const gradient = ctx.createRadialGradient(64,64,2,64,64,64);
  gradient.addColorStop(0,'rgba(255,255,255,0.6)');
  gradient.addColorStop(0.35,'rgba(255,255,255,0.35)');
  gradient.addColorStop(1,'rgba(255,255,255,0)');
  ctx.fillStyle = gradient; ctx.fillRect(0,0,128,128);
  return new THREE.CanvasTexture(canvas);
}

function Clouds({ reduced }) {
  const group = useRef();
  const texture = useMemo(makeCloudTexture,[]);
  useEffect(() => () => texture.dispose(),[texture]);
  const particles = useMemo(() => Array.from({length: 26},(_,i) => ({
    x: Math.sin(i * 13.7)*8, y: -1.8 + Math.cos(i*4.3)*1.3,
    z: -3 - (i%5), scale: 2.5 + (i%4)*0.7,
  })),[]);
  useFrame(({clock}) => { if(group.current && !reduced) group.current.position.x = Math.sin(clock.elapsedTime*0.05)*0.6; });
  return <group ref={group}>{particles.map((p,i) => <sprite key={i} position={[p.x,p.y,p.z]} scale={[p.scale*1.5,p.scale,1]}><spriteMaterial map={texture} opacity={0.75} transparent depthWrite={false} /></sprite>)}</group>;
}

function Bubbles({ power, reduced }) {
  const refs = useRef([]);
  useFrame(({clock}) => {
    if(reduced) return;
    refs.current.forEach((mesh,i) => {
      if(!mesh) return;
      const t = (clock.elapsedTime*(0.18+power*0.003)+i*0.089)%1;
      mesh.position.set(Math.sin(i*5.2+t*4)*0.37,-0.85+t*1.65,Math.cos(i*3.4)*0.37);
      mesh.scale.setScalar(0.015+(i%4)*0.008);
    });
  });
  return <group>{Array.from({length:36},(_,i)=><mesh key={i} ref={el=>refs.current[i]=el} position={[Math.sin(i)*0.35,-0.8+(i%12)*0.13,Math.cos(i)*0.35]} scale={0.025}><sphereGeometry args={[1,8,8]}/><meshStandardMaterial color="#e8ffef" metalness={0.3} roughness={0.12} transparent opacity={0.7}/></mesh>)}</group>;
}

export function Pod({ power=25, reduced=false }) {
  const pod = useRef();
  useFrame((state,delta) => {
    if(!pod.current) return;
    const scroll = Math.min(window.scrollY/window.innerHeight,1);
    pod.current.rotation.y = THREE.MathUtils.damp(pod.current.rotation.y,reduced?0.3:0.3+state.pointer.x*0.25+scroll*0.65,3,delta);
    pod.current.rotation.z = THREE.MathUtils.damp(pod.current.rotation.z,reduced?0.08:0.08+state.pointer.x*0.03,3,delta);
  });
  return <Float speed={reduced?0:1.3} rotationIntensity={reduced?0:0.09} floatIntensity={reduced?0:0.3}><group ref={pod} rotation={[0.06,0.3,0.08]}>
    <mesh position={[0,0,0]}><cylinderGeometry args={[0.66,0.66,2.5,64,1,true]}/><meshPhysicalMaterial color="#d9f1ef" transparent opacity={0.2} roughness={0.06} metalness={0.1} side={THREE.DoubleSide} depthWrite={false}/></mesh>
    <mesh position={[0,-0.12,0]}><cylinderGeometry args={[0.57,0.57,1.96,64]}/><meshPhysicalMaterial color="#4c927a" transparent opacity={0.75} roughness={0.22} metalness={0.12}/></mesh>
    <mesh position={[0,0.87,0]}><cylinderGeometry args={[0.565,0.565,0.018,64]}/><meshStandardMaterial color="#8ab59d" roughness={0.2}/></mesh>
    <Bubbles power={power} reduced={reduced}/>
    {[-1.18,1.18].map(y=><group key={y} position={[0,y,0]}>
      <mesh><cylinderGeometry args={[0.71,0.71,0.22,64]}/><meshStandardMaterial color="#e8ecef" roughness={0.3} metalness={0.5}/></mesh>
      <mesh position={[0,y>0?-0.15:0.15,0]} rotation={[Math.PI/2,0,0]}><torusGeometry args={[0.665,0.022,12,64]}/><meshStandardMaterial color="#b1e5d7" emissive="#77c8b1" emissiveIntensity={0.6+power*0.02}/></mesh>
      <mesh position={[0,y>0?0.12:-0.12,0]}><cylinderGeometry args={[0.6,0.68,0.04,64]}/><meshStandardMaterial color="#c4d8e5" roughness={0.3} metalness={0.4}/></mesh>
    </group>)}
    {[0,1,2,3,4,5,6,7].map(i=><mesh key={i} position={[Math.cos(i*Math.PI/4)*0.676,0,Math.sin(i*Math.PI/4)*0.676]}><cylinderGeometry args={[0.008,0.008,2.13,8]}/><meshStandardMaterial color="#d5eee5" emissive="#b1e5d7" emissiveIntensity={0.2+power*0.009}/></mesh>)}
    <mesh position={[0,-1.45,0]}><cylinderGeometry args={[0.63,0.73,0.35,64]}/><meshStandardMaterial color="#1c2b48" roughness={0.35} metalness={0.5}/></mesh>
    <RoundedBox args={[0.47,0.15,0.06]} radius={0.025} position={[0,-1.42,0.668]}><meshStandardMaterial color="#95bdd1" emissive="#8eb1d1" emissiveIntensity={0.35}/></RoundedBox>
    <mesh position={[0,1.39,0]}><cylinderGeometry args={[0.21,0.24,0.16,32]}/><meshStandardMaterial color="#1c2b48" metalness={0.35} roughness={0.4}/></mesh>
    <mesh position={[0.18,1.64,0]} rotation={[0,0,-0.65]}><cylinderGeometry args={[0.035,0.035,0.5,12]}/><meshStandardMaterial color="#c4d8e5" metalness={0.6} roughness={0.2}/></mesh>
    <mesh position={[0,-1.76,0]}><cylinderGeometry args={[0.82,0.82,0.05,64]}/><meshStandardMaterial color="#e8ecef" roughness={0.45} metalness={0.35}/></mesh>
  </group></Float>;
}

function HeroScene({ reduced, onReady }) {
  return <><ambientLight intensity={1.8}/><hemisphereLight args={['#ffffff','#8eb1d1',2]}/><directionalLight position={[4,5,5]} intensity={3}/><pointLight position={[-3,1,2]} intensity={20} color="#a7c7e7"/><Clouds reduced={reduced}/><group position={[0,0.2,0]} scale={1.22}><Pod reduced={reduced}/></group><Ready onReady={onReady}/></>;
}

export default function Atmosphere({ reduced, onReady }) {
  const [container,visible]=useSceneVisibility();
  const [available] = useState(() => {
    try { const c=document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch { return false; }
  });
  useEffect(() => { if(!available) onReady?.(); },[available,onReady]);
  return <div ref={container} className="canvas-container"><SceneBoundary onReady={onReady}>{available ? <Canvas dpr={[1,1.5]} camera={{position:[0,0.4,7],fov:38}} gl={{alpha:true,antialias:true,powerPreference:'low-power'}} frameloop={reduced||!visible?'demand':'always'}><Suspense fallback={null}><HeroScene reduced={reduced} onReady={onReady}/></Suspense></Canvas> : <div className="scene-fallback"><div className="fallback-pod"><span/><i/><b/></div></div>}</SceneBoundary></div>;
}

function WindowModel() {
  const {scene} = useGLTF('/models/window.glb');
  const model=useMemo(() => {
    const clone=scene.clone(true);
    const box=new THREE.Box3().setFromObject(clone);
    const size=box.getSize(new THREE.Vector3());
    const scale=3.1/Math.max(size.x,size.y,size.z);
    clone.scale.setScalar(scale);
    return clone;
  },[scene]);
  return <Center><primitive object={model} rotation={[0,-0.3,0]}/></Center>;
}

export function WindowScene({reduced}) {
  const [container,visible]=useSceneVisibility();
  return <div ref={container} className="canvas-container"><SceneBoundary><Canvas dpr={[1,1.5]} camera={{position:[0,0,6],fov:40}} frameloop={reduced||!visible?'demand':'always'}><ambientLight intensity={2}/><directionalLight position={[3,4,5]} intensity={3}/><Suspense fallback={null}><Float speed={reduced?0:1} rotationIntensity={0.08} floatIntensity={0.2}><WindowModel/></Float></Suspense></Canvas></SceneBoundary></div>;
}

export function DemoPod({power,reduced}) {
  const [container,visible]=useSceneVisibility();
  return <div ref={container} className="canvas-container"><SceneBoundary><Canvas dpr={[1,1.3]} camera={{position:[0,0,6],fov:40}} frameloop={reduced||!visible?'demand':'always'}><ambientLight intensity={2}/><directionalLight position={[3,5,4]} intensity={3}/><Pod power={power} reduced={reduced}/></Canvas></SceneBoundary></div>;
}
