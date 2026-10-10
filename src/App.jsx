import { useCallback, useEffect, useRef, useState } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import Lenis from 'lenis';
import { ArrowUpRight, Flame, Leaf, Menu, Wind, Activity, X } from 'lucide-react';
import { WindowScene } from './components/Atmosphere';
import OpeningJourney from './components/OpeningJourney';
import Preloader from './components/Preloader';
import SmokeTwin from './components/SmokeTwin';
import SmokeInterlude from './components/SmokeInterlude';
import ThemeSwitcher from './components/theme/ThemeSwitcher';
import SiteStars from './components/theme/SiteStars';
import { useThemeStore } from './stores/themeStore';
import './twin.css';
import './twin-experience.css';
import './mission.css';
gsap.registerPlugin(ScrollTrigger);
const CHAPTERS=[['01','Smoke twin','twin'],['02','Scenarios','scenarios'],['03','How it works','approach']];
function Brand({footer=false}) {return <a href="#home" className={'brand '+(footer?'brand-footer':'')} aria-label="Atmos home"><span className="brand-icon"><Leaf size={23} strokeWidth={1.5}/></span>atmos<span className="brand-registered">®</span></a>;}
function App() {
  const themeType=useThemeStore(state=>state.theme.type);
  const themeColor=useThemeStore(state=>state.theme.color);
  useEffect(()=>{document.documentElement.dataset.theme=themeType;document.documentElement.style.colorScheme=themeType;document.documentElement.style.setProperty('--sky-bg',themeColor);},[themeType,themeColor]);
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
    <SiteStars reduced={reduced}/>
    {!loaded&&<Preloader ready={sceneReady&&fontsReady} onComplete={finishLoader} reduced={reduced}/>}
    <a className="skip-link" href="#main">Skip to content</a>
    <header className={'site-header '+(scrolled?'is-scrolled ':'')+(active==='home'?'is-in-journey':'')}><Brand/><nav className="desktop-nav" aria-label="Main navigation">{CHAPTERS.map(([,title,id])=><a key={id} href={'#'+id} className={active===id?'active':''}>{title}</a>)}</nav><div className="header-actions"><ThemeSwitcher/><a href="#twin" className="header-cta">Explore the twin <ArrowUpRight size={16}/></a><button className="menu-toggle" aria-label={menu?'Close navigation':'Open navigation'} aria-expanded={menu} onClick={()=>setMenu(!menu)}>{menu?<X/>:<Menu/>}</button></div></header>
    {menu&&<nav className="mobile-nav" aria-label="Mobile navigation">{CHAPTERS.map(([number,title,id])=><a key={id} href={'#'+id} onClick={navigate}><span>{number}</span>{title}<ArrowUpRight/></a>)}</nav>}
    <main id="main" ref={main} inert={!loaded?true:undefined}>
      <OpeningJourney reduced={reduced} onReady={onReady}/>
      
      <section className="idea-section section-padding intro-section" id="idea"><div className="section-heading" data-reveal><span className="chapter-label">01 / THE IDEA</span></div><div className="idea-layout"><div data-reveal><h2>Smoke travels.<br/>Know what <em>arrives.</em></h2><p className="large-copy">A regional smoke twin for North India.</p><p className="body-copy">Connect crop-fire activity, wind and city air readings to estimate where smoke may travel and when it could arrive.</p><a href="#twin" className="underlined-link">Explore the smoke twin <ArrowUpRight size={19}/></a></div><div className="window-story" data-reveal><div className="window-glow"/><div className="window-3d" role="img" aria-label="Animated window, a frame for tracing smoke from fires toward downwind cities"><WindowScene reduced={reduced}/></div><p className="window-caption">A window into the smoke path.</p></div></div></section>
      <SmokeInterlude reduced={reduced}/>
      <section className="demo-section section-padding twin-section" id="twin"><div className="section-heading" data-reveal><span className="chapter-label">02 / THE SMOKE TWIN</span><span className="side-label">PUNJAB + HARYANA → DOWNWIND CITIES</span></div><div className="demo-intro" data-reveal><h2>Follow the <em>plume.</em></h2><div><p>Trace fire clusters through hourly wind. Select a city, replay stored history, or rerun the transport and forecast tools with a new scenario.</p></div></div><div data-reveal><SmokeTwin reduced={reduced}/></div></section>
      <section className="loop-section section-padding" id="scenarios"><div className="section-heading" data-reveal><span className="chapter-label">03 / SCENARIOS & IMPACT</span></div><div className="loop-intro" data-reveal><h2>From what-if<br/>to <em>what next.</em></h2><p>Make uncertainty visible. Turn a forecast into a decision.</p></div><div className="loop-grid">{[{number:'01',icon:Wind,title:'Explore a shift.',description:'Change wind direction to explore a different downwind path and arrival estimate.',graphic:'air'},{number:'02',icon:Flame,title:'Stress-test fires.',description:'Change fire activity and rerun the available forecast model.',graphic:'light'},{number:'03',icon:Activity,title:'Plan for people.',description:'Translate a regional outlook into school, hospital and district impact views.',graphic:'cloud'}].map(item=><article className="loop-card" key={item.number} data-reveal><div className="loop-card-top"><span>{item.number}</span><item.icon size={24} strokeWidth={1}/></div><div className={'loop-graphic graphic-'+item.graphic} aria-hidden="true">{item.graphic==='air'?<><i/><i/><i/><i/><i/><i/></>:item.graphic==='light'?<><span/><i/><i/><i/></>:<><Activity size={70} strokeWidth={0.8}/><span/><i/><i/></>}</div><h3>{item.title}</h3><p>{item.description}</p></article>)}</div><p className="prototype-note" data-reveal><span>ADVISORY PRINCIPLE</span> Guidance should reflect the selected audience and cite the signals behind it. Use the tool evidence alongside official local guidance.</p></section>
      <section className="architecture-section section-padding" id="approach"><div className="section-heading" data-reveal><span className="chapter-label">04 / DATA & METHOD</span><span className="side-label">SOURCES, MODELS & UNCERTAINTY</span></div><div className="architecture-intro" data-reveal><h2>Grounded in <em>signals.</em></h2><p>Agents call data and models as tools; they should never invent measurements.</p></div><div className="architecture-flow" data-reveal>{[['01','Fire detections','NASA FIRMS hotspots · API key needed'],['02','Wind transport','Open-Meteo hourly wind · integrated drift'],['03','City air','OpenAQ hourly PM2.5 · station CSV imports'],['04','Forecast + explain','Time-based backtest · intervals · feature reasons']].map(([n,title,sub])=><div key={n}><span>{n}<ArrowUpRight size={16}/></span><h3>{title}</h3><p>{sub}</p></div>)}</div><div className="architecture-branches" data-reveal><span>STORE + REFRESH <strong>SQLite · hourly provider refresh</strong></span><span>MODEL COMPARISON <strong>Persistence · Ridge · XGBoost · LightGBM</strong></span></div><div className="limits-note" data-reveal><b>KNOWN LIMITS</b><span>Satellites can miss fires. Stubble smoke is only one contributor to PM2.5. Simple wind drift is an estimate; HYSPLIT could be a later transport upgrade. Real forecasts require sufficient station and fire history; demo models remain synthetic.</span></div></section>
      <section className="closing-section" id="vision"><div className="closing-cloud"/><h2 data-reveal>See smoke <em>coming.</em></h2><a href="#twin" className="button button-dark" data-reveal>Open the twin <ArrowUpRight size={18}/></a><div className="closing-word" aria-hidden="true">atmos</div></section>
    </main>
    <footer><div><Brand footer/><p>See where smoke may travel next.</p></div><div className="footer-links"><a href="https://www.wemakedevs.org/aws/env" target="_blank" rel="noreferrer">Environmental Hacks <ArrowUpRight size={14}/></a><a href="#approach">Data & method <ArrowUpRight size={14}/></a><button onClick={()=>{window.scrollTo({top:0,behavior:'instant'});setLoaded(false);}}>Replay intro <ArrowUpRight size={14}/></button></div><div className="footer-meta"><span>Research prototype · Check data mode</span><button onClick={()=>setReduced(!reduced)} aria-pressed={reduced}>Motion {reduced?'off':'on'} <span className={'motion-switch '+(reduced?'off':'')}/></button></div></footer>
  </>;
}
export default App;
