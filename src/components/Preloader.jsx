import { useEffect, useRef } from 'react';
import gsap from 'gsap';
export default function Preloader({ready,onComplete,reduced}) {
  const root=useRef();
  const started=useRef(Date.now());
  useEffect(() => {
    if(!ready) return;
    const delay=reduced?0:Math.max(0,1400-(Date.now()-started.current))/1000;
    const timeline=gsap.timeline({delay,onComplete});
    timeline.to(root.current.querySelector('.loader-symbol'),{scale:0.6,opacity:0,duration:reduced?0:0.65,ease:'power3.inOut'})
      .to(root.current,{yPercent:-100,duration:reduced?0:0.9,ease:'power4.inOut'},reduced?0:'-=0.3');
    return () => timeline.kill();
  },[ready,reduced,onComplete]);
  return <div ref={root} className="preloader" role="status" aria-label="Opening AlgaeAir"><span className="loader-brand">algaeair<span>®</span></span><div className="loader-symbol"><svg viewBox="0 0 200 110" aria-hidden="true"><path className="loader-orbit" d="M100 55C55-18 5 16 17 62c10 42 54 29 83-7 29-36 73-49 83-7 12 46-38 80-83 7Z"/><circle className="loader-dot" r="9"><animateMotion dur="2.5s" repeatCount="indefinite" path="M100 55C55-18 5 16 17 62c10 42 54 29 83-7 29-36 73-49 83-7 12 46-38 80-83 7Z"/></circle></svg><span>A breath of something better.</span></div><div className="loader-bottom"><span>GROWING POSSIBILITIES</span><span>{ready?'READY TO BREATHE':'OPENING YOUR ATMOSPHERE'}</span></div></div>;
}
