import { Component, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { ArrowUpRight, Flame, Wind, Activity } from 'lucide-react';
import { useThemeStore } from '../stores/themeStore';
import gsap from 'gsap';

const vertexShader=`varying vec2 vUv; void main(){vUv=uv;gl_Position=vec4(position.xy,0.0,1.0);}`;
const fragmentShader=`
precision highp float;
varying vec2 vUv;
uniform float uTime; uniform vec2 uPointer; uniform float uDark;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(hash(i),hash(i+vec2(1.,0.)),f.x),mix(hash(i+vec2(0.,1.)),hash(i+1.),f.x),f.y);}
float fbm(vec2 p){float v=0.,a=.5;for(int i=0;i<5;i++){v+=a*noise(p);p=p*2.03+vec2(8.1,4.3);a*=.5;}return v;}
void main(){
 vec2 p=(vUv-.5)*vec2(1.65,1.);p+=uPointer*.045;
 float t=uTime*.055;
 vec2 q=vec2(fbm(p*2.2+vec2(t,-t*.5)),fbm(p*2.2+vec2(3.4,t)));
 vec2 r=vec2(fbm(p*3.+q*2.8+vec2(t*.4,1.2)),fbm(p*2.8+q*2.4+vec2(8.2,-t*.3)));
 float clouds=fbm(p*3.5+r*3.2);float centre=1.-smoothstep(.08,.85,length(p+vec2(0.,.03)));
 float waves=sin((p.y+clouds*.23)*12.+p.x*2.+t)*.5+.5;
 vec3 blue=mix(vec3(.047,.36,.51),vec3(.55,.74,.78),clouds);
 vec3 amber=mix(vec3(.55,.22,.095),vec3(.85,.62,.44),clouds);
 vec3 col=mix(blue,amber,smoothstep(.08,.8,1.-vUv.y)*.65);
 col=mix(col,vec3(.88,.9,.84),centre*.84);col+=waves*.045;
 vec3 dark=mix(vec3(.025,.055,.075),col*.37,clouds*.9);col=mix(col,dark,uDark);
 float grain=(hash(vUv*vec2(1920.,1080.)+floor(uTime*8.))-.5)*.024;
 gl_FragColor=vec4(col+grain,1.);
}`;

class AtmosphereBoundary extends Component {
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true}};
  render(){return this.state.failed?null:this.props.children}
}
function SmokeSurface({reduced,dark}) {
  const material=useRef();
  const uniforms=useMemo(()=>({uTime:{value:0},uPointer:{value:{x:0,y:0}},uDark:{value:dark?1:0}}),[]);
  useEffect(()=>{if(reduced&&material.current)material.current.uniforms.uDark.value=Number(dark)},[reduced,dark]);
  useFrame((state,delta)=>{
    if(!material.current)return;
    if(!reduced)material.current.uniforms.uTime.value+=Math.min(delta,.05);
    material.current.uniforms.uPointer.value.x+=(state.pointer.x-material.current.uniforms.uPointer.value.x)*.035;
    material.current.uniforms.uPointer.value.y+=(state.pointer.y-material.current.uniforms.uPointer.value.y)*.035;
    material.current.uniforms.uDark.value+=(Number(dark)-material.current.uniforms.uDark.value)*.04;
  });
  return <mesh frustumCulled={false}><planeGeometry args={[2,2]}/><shaderMaterial ref={material} uniforms={uniforms} vertexShader={vertexShader} fragmentShader={fragmentShader} depthTest={false} depthWrite={false}/></mesh>;
}

export default function SmokeInterlude({reduced}) {
  const ref=useRef();
  const [visible,setVisible]=useState(false);
  const dark=useThemeStore(state=>state.theme.type)==='dark';
  useEffect(()=>{
    const observer=new IntersectionObserver(([entry])=>setVisible(entry.isIntersecting),{rootMargin:'150px'});observer.observe(ref.current);return()=>observer.disconnect();
  },[]);
  useEffect(()=>{
    if(reduced)return;
    const context=gsap.context(()=>{
      gsap.fromTo('.interlude-copy h2 span',{y:55,opacity:0},{y:0,opacity:1,stagger:.14,duration:1.5,ease:'power3.out',scrollTrigger:{trigger:ref.current,start:'top 70%',once:true}});
      gsap.to('.interlude-orbit',{rotate:22,scrollTrigger:{trigger:ref.current,start:'top bottom',end:'bottom top',scrub:1.8}});
    },ref);return()=>context.revert();
  },[reduced]);
  return <section ref={ref} className="smoke-interlude" id="atmosphere" aria-label="From fire to forecast atmospheric interlude">
    <div className="interlude-surface"><div className="interlude-fallback"/><AtmosphereBoundary><Canvas dpr={[1,1.5]} frameloop={visible&&!reduced?'always':'demand'} gl={{antialias:false,alpha:true}}><SmokeSurface reduced={reduced} dark={dark}/></Canvas></AtmosphereBoundary></div>
    <div className="interlude-top"><span><i/> AN ATMOSPHERE IN MOTION</span><span>01 FIRES → 02 WIND → 03 CITIES</span></div>
    <div className="interlude-orbit" aria-hidden="true"/>
    <div className="interlude-copy"><span className="chapter-label">THE SIGNAL BETWEEN THE SOURCES</span><h2><span>From a spark.</span><span>Through the sky.</span><span><em>To a clearer outlook.</em></span></h2><p>Trace the signals that connect a field to a city.</p><a href="#twin" className="button button-dark">Follow the atmosphere <ArrowUpRight size={18}/></a></div>
    <div className="interlude-foot"><div className="interlude-palette"><span><Flame size={17}/> Fire</span><span><Wind size={17}/> Wind</span><span><Activity size={17}/> Air</span></div><span>ESTIMATES WITH EVIDENCE.<br/>UNCERTAINTY IN THE OPEN.</span></div>
  </section>;
}
