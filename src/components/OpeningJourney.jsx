import { Component, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Cloud, Clouds } from '@react-three/drei/core/Cloud.js';
import { Text } from '@react-three/drei/core/Text.js';
import { useGLTF } from '@react-three/drei/core/Gltf.js';
import { ArrowDown, ArrowRight, ArrowUpRight } from 'lucide-react';
import * as THREE from 'three';
import { Pod } from './Atmosphere';
import gsap from 'gsap';
import { useThemeStore } from '../stores/themeStore';
import StarsContainer from './theme/Stars';
import { clamp01, range, smoothRange, sampleJourney, journeyPhase } from './journeyPath';

const FONT = '/fonts/jizBRFtNs2ka5fXjeivQ4LroWlx-2zI.ttf';
const ITALIC_FONT = '/fonts/jizHRFtNs2ka5fXjeivQ4LroWlx-6zATiw.ttf';
const PHASE_LABELS = {sky:'01 / ABOVE THE CLOUDS',clouds:'02 / INTO THE ATMOSPHERE',window:'03 / A WINDOW TO BETTER AIR',emerge:'04 / THROUGH TO THE OTHER SIDE',pod:'05 / MEET ALGAEAIR'};

function supportsWebGL() {
  try {
    const canvas=document.createElement('canvas');
    const context=canvas.getContext('webgl2') || canvas.getContext('webgl');
    const supported=!!context;
    context?.getExtension('WEBGL_lose_context')?.loseContext();
    return supported;
  } catch { return false; }
}

class JourneyBoundary extends Component {
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  componentDidCatch(){this.props.onReady?.();}
  render(){return this.state.failed?this.props.fallback:this.props.children;}
}

function ScrollCamera({signal,frameRequest,reduced,viewport,modelReady}) {
  const progress=useRef(0);
  const pod=useRef();
  const {invalidate,size}=useThree();
  useEffect(()=>{frameRequest.current=invalidate;return()=>{frameRequest.current=null;};},[frameRequest,invalidate]);
  useFrame((state,delta)=>{
    progress.current=reduced?signal.current:THREE.MathUtils.damp(progress.current,signal.current,7,Math.min(delta,0.05));
    const p=progress.current;
    const path=sampleJourney(p);
    state.camera.position.set(path.x,path.y,path.z);
    state.camera.rotation.set(path.pitch,reduced?0:-state.pointer.x*Math.PI/90,0,'YXZ');
    state.camera.updateMatrixWorld();
    if(pod.current)pod.current.visible=path.podVisible;
    if(viewport.current){
      viewport.current.style.setProperty('--entry-opacity',1-smoothRange(p,0.05,0.15));
      viewport.current.style.setProperty('--pod-opacity',smoothRange(p,0.8,0.06));
      viewport.current.style.setProperty('--pod-offset',(1-smoothRange(p,0.8,0.06))*30+'px');
      viewport.current.dataset.cameraProgress=p.toFixed(4);
      viewport.current.dataset.cameraY=path.y.toFixed(3);
      viewport.current.dataset.cameraPitch=path.pitch.toFixed(3);
    }
  },-1);
  return <group ref={pod} visible={false} position={[size.width<760?0:2.35,size.width<760?-33.1:-31.35,0]} scale={size.width<760?0.7:1.25}><Pod reduced={reduced}/></group>;
}

function JourneyClouds({reduced}) {
  // Match the reference's seeded, slowly expanding cloud banks and depth distribution.
  const banks=[
    {seed:1,position:[-1,0,0],bounds:[10,10,10],scale:1.9,volume:2,growth:3,fade:5,speed:0.2,concentrate:'inside'},
    {seed:3,position:[2,0,2],bounds:[10,10,10],scale:1,volume:2,growth:2,fade:3,speed:0.1,concentrate:'outside'},
    {seed:4,position:[-10,-10,4],bounds:[10,20,15],scale:2,volume:3,growth:4,fade:8,speed:0.2,concentrate:'outside'},
    {seed:5,position:[6,-3,8],bounds:[5,5,5],scale:2,volume:2,growth:2,fade:4,speed:0.1,concentrate:'outside'},
    {seed:6,position:[0,-20,20],bounds:[5,5,5],scale:4,volume:3,growth:2,fade:4,speed:0.1,concentrate:'outside'},
    {seed:7,position:[10,-15,-5],bounds:[5,5,5],scale:3,volume:3,growth:2,fade:4,speed:0.1,concentrate:'outside'},
  ];
  return <Clouds material={THREE.MeshBasicMaterial} texture="/textures/cloud.png" position={[0,-5,0]} limit={60} frustumCulled={false}>
    {banks.map(bank=><Cloud key={bank.seed} {...bank} segments={1} smallestVolume={2} speed={reduced?0:bank.speed} color="#e8ecef"/>) }
    <Cloud seed={21} position={[-6,-8,5]} bounds={[2,2,3]} segments={4} volume={3.1} growth={1.8} opacity={0.85} fade={5} speed={reduced?0:0.09}/>
    <Cloud seed={22} position={[6,-13,4]} bounds={[2,2,3]} segments={4} volume={3} growth={1.8} opacity={0.85} fade={5} speed={reduced?0:0.1}/>
    <Cloud seed={23} position={[-7,-20,3]} bounds={[2,2,3]} segments={4} volume={3.6} growth={1.2} opacity={0.8} fade={4} speed={reduced?0:0.07}/>
    <Cloud seed={24} position={[7,-22,5]} bounds={[2,2,3]} segments={4} volume={3.5} growth={1.2} opacity={0.8} fade={4} speed={reduced?0:0.09}/>
    <Cloud seed={25} position={[-6,-28,-4]} bounds={[2,1,2]} segments={3} volume={3} growth={1} opacity={0.35} fade={5} speed={reduced?0:0.07}/>
  </Clouds>;
}

function FloatingWindow({signal,reduced,onReady}) {
  const {nodes,materials}=useGLTF('/models/window.glb','/draco/');
  const sash=useRef();const handle=useRef();const current=useRef(0);
  const material=useMemo(()=>{
    const clone=materials.WIN0003_Textures.clone();
    clone.transmission=0;clone.roughness=0.35;
    return clone;
  },[materials]);
  useEffect(()=>{onReady?.();return()=>material.dispose();},[onReady,material]);
  useFrame((state,delta)=>{
    current.current=reduced?signal.current:THREE.MathUtils.damp(current.current,signal.current,7,Math.min(delta,0.05));
    const path=sampleJourney(current.current);
    if(sash.current)sash.current.rotation.z=path.sash;
    if(handle.current)handle.current.rotation.y=path.handle;
  });
  return <group position={[0,-25,5.69]} dispose={null}>
    <pointLight position={[1,1,-2.5]} intensity={35} distance={12}/>
    <group rotation={[0,Math.PI,Math.PI]}>
      <mesh geometry={nodes['#WIN0003_Frame_#WIN0003_Textures_0'].geometry} material={material}/>
      <group position={[0.441,-0.039,0.082]} ref={sash}>
        <mesh geometry={nodes['#WIN0003_Window_#WIN0003_Textures_0'].geometry} material={material}/>
        <mesh ref={handle} geometry={nodes['#WIN0003_Handle_#WIN0003_Textures_0'].geometry} material={material} position={[-0.84,-0.018,0.55]}/>
      </group>
    </group>
  </group>;
}

function SkyTitle() {
  const {size}=useThree();
  const fontSize=size.width<760?0.54:1.1;
  return <group position={[0,2,-10]}>
    <Text font={FONT} fontSize={fontSize} color="#ffffff" anchorX="center" anchorY="middle" position={[0,0.6,0]} characters="A little algae.">A little algae.</Text>
    <Text font={ITALIC_FONT} fontSize={fontSize} color="#ffffff" anchorX="center" anchorY="middle" position={[0,-0.7,0]} characters="A better atmosphere.">A better atmosphere.</Text>
  </group>;
}

function Scene({signal,frameRequest,reduced,viewport,onReady}) {
  return <>
    <ambientLight intensity={1.6}/><hemisphereLight args={['#ffffff','#8eb1d1',1.5]}/>
    <directionalLight position={[5,5,8]} intensity={2}/>
    <directionalLight position={[-4,-20,10]} intensity={1.4}/>
    <pointLight position={[0,-28,6]} intensity={20} color="#a7c7e7"/>
    <StarsContainer reduced={reduced}/>
    <JourneyClouds reduced={reduced}/>
    <SkyTitle/>
    <FloatingWindow signal={signal} reduced={reduced} onReady={onReady}/>
    <ScrollCamera signal={signal} frameRequest={frameRequest} reduced={reduced} viewport={viewport}/>
  </>;
}

function FlatJourney({signal}) {
  return <div className="flat-journey" aria-hidden="true">
    <div className="flat-cloud flat-cloud-one"/><div className="flat-cloud flat-cloud-two"/><div className="flat-cloud flat-cloud-three"/>
    <div className="flat-window"><div className="flat-sash"><span/></div></div>
    <div className="flat-pod"><div className="fallback-pod"><span/></div></div>
  </div>;
}

export default function OpeningJourney({reduced,onReady}) {
  const backgroundColor=useThemeStore(state=>state.theme.color);
  const themeType=useThemeStore(state=>state.theme.type);
  const backgroundRef=useRef();
  const track=useRef();const viewport=useRef();const signal=useRef(0);const frameRequest=useRef();
  const [phase,setPhase]=useState('sky');const [visible,setVisible]=useState(true);
  const [available]=useState(supportsWebGL);
  useEffect(()=>{if(!available)onReady?.();},[available,onReady]);
  useEffect(()=>{
    const node=track.current;const stage=viewport.current;
    let frame=0;
    const update=()=>{
      frame=0;
      const rect=node.getBoundingClientRect();
      const scrollLength=Math.max(1,node.offsetHeight-stage.offsetHeight);
      const p=clamp01(-rect.top/scrollLength);
      signal.current=p;
      const currentPhase=journeyPhase(p);setPhase(previous=>previous===currentPhase?previous:currentPhase);
      stage.style.setProperty('--journey-progress',p);
      stage.style.setProperty('--window-opacity',smoothRange(p,0.4,0.08)*(1-smoothRange(p,0.64,0.04)));
      stage.style.setProperty('--window-scale',0.5+range(p,0.42,0.21)*6);
      stage.style.setProperty('--sash-angle',range(p,0.5,0.1)*95+'deg');
      stage.style.setProperty('--entry-opacity',1-smoothRange(p,0.05,0.15));
      stage.style.setProperty('--pod-opacity',smoothRange(p,0.8,0.06));
      stage.style.setProperty('--pod-offset',(1-smoothRange(p,0.8,0.06))*30+'px');
      stage.dataset.progress=p.toFixed(4);
      frameRequest.current?.();
    };
    const requestUpdate=()=>{if(!frame)frame=requestAnimationFrame(update);};
    update();window.addEventListener('scroll',requestUpdate,{passive:true});window.addEventListener('resize',requestUpdate);
    const observer=new IntersectionObserver(([entry])=>{setVisible(entry.isIntersecting);frameRequest.current?.();});observer.observe(node);
    return()=>{window.removeEventListener('scroll',requestUpdate);window.removeEventListener('resize',requestUpdate);observer.disconnect();cancelAnimationFrame(frame);};
  },[]);
  // Background transition and grain copied from upstream CanvasLoader.tsx.
  useEffect(()=>{
    const noiseOverlayStyle = {
      backgroundBlendMode: "soft-light",
      backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 600'%3E%3Cfilter id='a'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23a)'/%3E%3C/svg%3E\")",
      backgroundRepeat: "repeat",
      backgroundSize: "100px",
    };
    const animation=gsap.to(backgroundRef.current,{backgroundColor,duration:reduced?0:1,...noiseOverlayStyle});
    frameRequest.current?.();
    return()=>animation.kill();
  },[backgroundColor,reduced]);
  const fallback=<FlatJourney signal={signal}/>;
  return <section id="home" ref={track} className="opening-journey" aria-label="Cloud-to-window scroll journey">
    <div id="prototype" className="prototype-anchor"/>
    <div ref={viewport} className={'opening-viewport '+(!available?'no-webgl':'')} data-phase={phase} data-theme={themeType}>
      <div ref={backgroundRef} className="journey-canvas" role="img" aria-label="Scroll through floating clouds, pass through an opening window, and emerge beside the AlgaeAir bioreactor">
        <JourneyBoundary fallback={fallback} onReady={onReady}>
          {available?<Canvas dpr={[1,1.5]} camera={{position:[0,0,5],fov:40,near:0.01,far:1000}} gl={{alpha:true,antialias:true}} frameloop={reduced||!visible?'demand':'always'}><Suspense fallback={null}><Scene signal={signal} frameRequest={frameRequest} reduced={reduced} viewport={viewport} onReady={onReady}/></Suspense></Canvas>:fallback}
        </JourneyBoundary>
      </div>
      <div className="journey-entry">
        
        <h1 className={available?'journey-accessible-title':'journey-flat-title'}>A little algae.<br/>A better atmosphere.</h1>
        
      </div>
      <a className="journey-skip" href="#prototype">Meet the pod <ArrowDown size={13}/></a>
      
      <div className="journey-product" inert={phase!=='pod'?true:undefined}>
        
        <h2>Meet your<br/><em>living air pod.</em></h2>
        <p>Microalgae. Adaptive light. Connected controls.</p>
        <div className="hero-buttons"><a href="#idea" className="button button-dark">Discover AlgaeAir <ArrowUpRight size={18}/></a><a href="#demo" className="hero-secondary">See it respond <span><ArrowRight size={17}/></span></a></div>
        
      </div>
      <div className="journey-footer"><span className="journey-scroll"><ArrowDown size={14}/> {phase==='pod'?'Explore below':'Scroll to explore'}</span><div className="journey-progress" aria-hidden="true"><span/></div></div>
    </div>
  </section>;
}
