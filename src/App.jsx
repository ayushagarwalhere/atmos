import { useCallback, useEffect, useRef, useState } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import Lenis from 'lenis';
import { ArrowDown, ArrowRight, ArrowUpRight, Cloud, Leaf, Menu, Radio, Sun, Wind, X } from 'lucide-react';
import { WindowScene } from './components/Atmosphere';
import OpeningJourney from './components/OpeningJourney';
import Preloader from './components/Preloader';
import DemoConsole from './components/DemoConsole';
import ThemeSwitcher from './components/theme/ThemeSwitcher';
import { useThemeStore } from './stores/themeStore';
gsap.registerPlugin(ScrollTrigger);
const CHAPTERS=[['01','The idea','idea'],['02','The living loop','loop'],['03','Try the response','demo']];
function Brand({footer=false}) {return <a href="#home" className={'brand '+(footer?'brand-footer':'')} aria-label="AlgaeAir home"><span className="brand-icon"><Leaf size={23} strokeWidth={1.5}/></span>algaeair<span className="brand-registered">®</span></a>;}
function App() {
  const themeType=useThemeStore(state=>state.theme.type);
  useEffect(()=>{document.documentElement.dataset.theme=themeType;document.documentElement.style.colorScheme=themeType;},[themeType]);
  const [reduced,setReduced]=useState(()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const [sceneReady,setSceneReady]=useState(false);
  const [fontsReady,setFontsReady]=useState(false);
  const [loaded,setLoaded]=useState(false);
  const [menu,setMenu]=useState(false);
  const [active,setActive]=useState('home');
  const [scrolled,setScrolled]=useState(false);
  const main=useRef();
  const onReady=useCallback(()=>setSceneReady(true),[]);
  const finishLoader=useCallback(()=>setLoaded(true),[]);
  useEffect(()=>{document.fonts.ready.then(()=>setFontsReady(true));const media=window.matchMedia('(prefers-reduced-motion: reduce)');const change=e=>setReduced(e.matches);media.addEventListener('change',change);return()=>media.removeEventListener('change',change);},[]);
  useEffect(()=>{document.body.style.overflow=loaded?'':'hidden';return()=>{document.body.style.overflow='';};},[loaded]);
  useEffect(()=>{
    if(!loaded) return;
    let lenis; let tick;
    if(!reduced) {lenis=new Lenis({duration:1.15,smoothWheel:true,anchors:true});lenis.on('scroll',ScrollTrigger.update);tick=time=>lenis.raf(time*1000);gsap.ticker.add(tick);}
    const context=gsap.context(()=>{
      if(!reduced) {
        gsap.utils.toArray('[data-reveal]').forEach(el=>{gsap.from(el,{y:45,opacity:0,duration:0.95,ease:'power3.out',scrollTrigger:{trigger:el,start:'top 90%',once:true}});});
      }
    },main);
    const sections=Array.from(document.querySelectorAll('main section[id]'));
    const observer=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(entry.isIntersecting)setActive(entry.target.id);});},{rootMargin:'-25% 0px -45% 0px'});
    sections.forEach(section=>observer.observe(section));
    const scroll=()=>setScrolled(window.scrollY>50);window.addEventListener('scroll',scroll,{passive:true});
    return()=>{context.revert();observer.disconnect();window.removeEventListener('scroll',scroll);if(tick)gsap.ticker.remove(tick);lenis?.destroy();};
  },[loaded,reduced]);
  function navigate() {setMenu(false);}
  return <>
    {!loaded&&<Preloader ready={sceneReady&&fontsReady} onComplete={finishLoader} reduced={reduced}/>}
    <a className="skip-link" href="#main">Skip to content</a>
    <header className={'site-header '+(scrolled?'is-scrolled ':'')+(active==='home'?'is-in-journey':'')}><Brand/><nav className="desktop-nav" aria-label="Main navigation">{CHAPTERS.map(([,title,id])=><a key={id} href={'#'+id} className={active===id?'active':''}>{title}</a>)}</nav><div className="header-actions"><ThemeSwitcher/><a href="#prototype" className="header-cta">Explore the pod <ArrowUpRight size={16}/></a><button className="menu-toggle" aria-label={menu?'Close navigation':'Open navigation'} aria-expanded={menu} onClick={()=>setMenu(!menu)}>{menu?<X/>:<Menu/>}</button></div></header>
    {menu&&<nav className="mobile-nav" aria-label="Mobile navigation">{CHAPTERS.map(([number,title,id])=><a key={id} href={'#'+id} onClick={navigate}><span>{number}</span>{title}<ArrowUpRight/></a>)}</nav>}
    <main id="main" ref={main} inert={!loaded?true:undefined}>
      <OpeningJourney reduced={reduced} onReady={onReady}/>
      
      <section className="idea-section section-padding" id="idea"><div className="section-heading" data-reveal><span className="chapter-label">01 / THE IDEA</span></div><div className="idea-layout"><div data-reveal><h2>What if better air<br/>could <em>grow?</em></h2><p className="large-copy">A living air pod for classrooms.</p><p className="body-copy">Microalgae, sensors and adaptive controls work together in one compact bioreactor.</p><a href="#loop" className="underlined-link">Meet the living loop <ArrowUpRight size={19}/></a></div><div className="window-story" data-reveal><div className="window-glow"/><div className="window-3d" role="img" aria-label="Floating window frame, a symbol of bringing better air into classrooms"><WindowScene reduced={reduced}/></div></div></div></section>
      <section className="loop-section section-padding" id="loop"><div className="section-heading" data-reveal><span className="chapter-label">02 / THE LIVING LOOP</span></div><div className="loop-intro" data-reveal><h2>One pod.<br/><em>Three essentials.</em></h2><p>Air, light and a connected response.</p></div><div className="loop-grid">{[{number:'01',icon:Wind,title:'Let the air in.',description:'A pump circulates air through the chamber.',tag:'AIR AGITATION',graphic:'air'},{number:'02',icon:Sun,title:'Find the right light.',description:'Sensors adjust the growth lights to ambient conditions.',tag:'ADAPTIVE ILLUMINATION',graphic:'light'},{number:'03',icon:Cloud,title:'Listen. Then respond.',description:'Air-quality readings guide pod controls and classroom alerts.',tag:'CONNECTED CONTROL',graphic:'cloud'}].map(item=><article className="loop-card" key={item.number} data-reveal><div className="loop-card-top"><span>{item.number}</span><item.icon size={24} strokeWidth={1}/></div><div className={'loop-graphic graphic-'+item.graphic} aria-hidden="true">{item.graphic==='air'?<><i/><i/><i/><i/><i/><i/></>:item.graphic==='light'?<><span/><i/><i/><i/></>:<><Cloud size={80} strokeWidth={0.7}/><span/><i/><i/></>}</div><h3>{item.title}</h3><p>{item.description}</p></article>)}</div><p className="prototype-note" data-reveal><span>THE FIRST PROTOTYPE</span> The prototype uses dyed water. Air-cleaning performance is not yet measured.</p></section>
      <section className="demo-section section-padding" id="demo"><div className="section-heading" data-reveal><span className="chapter-label">03 / TRY THE RESPONSE</span></div><div className="demo-intro" data-reveal><h2>See the <em>response.</em></h2><div><p>Trigger a smog event. Watch the pod respond.</p></div></div><div data-reveal><DemoConsole reduced={reduced}/></div></section>
      <section className="architecture-section section-padding" id="architecture"><div className="section-heading" data-reveal><span className="chapter-label">04 / BEHIND THE BREATH</span></div><div className="architecture-intro" data-reveal><h2>How it <em>connects.</em></h2><p>The planned connection from sensor to pod.</p></div><div className="architecture-flow" data-reveal>{[['01','Ambient AQI','Regional data source'],['02','AWS IoT Core','Secure device messaging'],['03','AWS Lambda','Evaluate control rules'],['04','ESP32 pod','Apply pump + LED settings']].map(([n,title,sub])=><div key={n}><span>{n}<ArrowRight size={16}/></span><h3>{title}</h3><p>{sub}</p></div>)}</div><div className="architecture-branches" data-reveal><span>RECORD THE RESPONSE <ArrowRight size={16}/> <strong>DynamoDB</strong></span><span>NOTIFY THE CLASSROOM <ArrowRight size={16}/> <strong>Amazon SNS</strong></span></div></section>
      <section className="closing-section" id="vision"><div className="closing-cloud"/><h2 data-reveal>A fresher <em>possibility.</em></h2><a href="#demo" className="button button-dark" data-reveal>Try the demo <ArrowUpRight size={18}/></a><div className="closing-word" aria-hidden="true">algaeair</div></section>
    </main>
    <footer><div><Brand footer/><p>A little algae. A better atmosphere.</p></div><div className="footer-links"><a href="https://www.wemakedevs.org/aws/env" target="_blank" rel="noreferrer">Environmental Hacks <ArrowUpRight size={14}/></a><a href="#architecture">The architecture <ArrowUpRight size={14}/></a><button onClick={()=>{window.scrollTo({top:0,behavior:'instant'});setLoaded(false);}}>Replay intro <ArrowUpRight size={14}/></button></div><div className="footer-meta"><span>Prototype · <a href="/credits.txt" target="_blank" rel="noreferrer">3D credits</a></span><button onClick={()=>setReduced(!reduced)} aria-pressed={reduced}>Motion {reduced?'off':'on'} <span className={'motion-switch '+(reduced?'off':'')}/></button></div></footer>
  </>;
}
export default App;
