import { useEffect, useRef, useState } from 'react';
import { Activity, ArrowUpRight, Check, ChevronDown, Download, Droplets, Lightbulb, Play, RotateCcw, Wind } from 'lucide-react';
import { DemoPod } from './Atmosphere';
const STAGES=['Ambient reading','Cloud calculation','Pod response','Classroom alert'];
const ZONES={Delhi:{aqi:78,smog:412},Mumbai:{aqi:64,smog:235},Bengaluru:{aqi:42,smog:187}};
function controlsFor(aqi) { return {pump:aqi>300?100:aqi>200?75:aqi>100?50:25,light:aqi>300?100:aqi>200?80:aqi>100?60:35}; }
export default function DemoConsole({reduced}) {
  const [zone,setZone]=useState('Delhi');
  const [aqi,setAqi]=useState(78);
  const [deviceAqi,setDeviceAqi]=useState(78);
  const [step,setStep]=useState(-1);
  const [running,setRunning]=useState(false);
  const [mode,setMode]=useState('baseline');
  const [events,setEvents]=useState([]);
  const timers=useRef([]);
  const {pump,light}=controlsFor(deviceAqi);
  const status=aqi>300?'Severe':aqi>200?'Poor':aqi>100?'Moderate':'Satisfactory';
  const clearTimers=()=>{timers.current.forEach(clearTimeout);timers.current=[];};
  useEffect(()=>()=>clearTimers(),[]);
  const log=(message)=>setEvents(prev=>[{time:new Date().toLocaleTimeString('en-IN',{hour12:false}),message},...prev].slice(0,6));
  function reset(nextZone=zone) {clearTimers();setRunning(false);setMode('baseline');setAqi(ZONES[nextZone].aqi);setDeviceAqi(ZONES[nextZone].aqi);setStep(-1);setEvents([]);}
  function trigger() {
    clearTimers();setRunning(true);setStep(0);setMode('smog');setAqi(ZONES[zone].smog);
    log('Sample '+zone+' pollution reading received.');
    const actions=[()=>{setStep(1);log('Local rule evaluated: AQI threshold exceeded.');},()=>{setStep(2);setDeviceAqi(ZONES[zone].smog);log('Simulated command: pump '+controlsFor(ZONES[zone].smog).pump+'%, growth lights '+controlsFor(ZONES[zone].smog).light+'%.');},()=>{setStep(3);setRunning(false);log('Classroom 4B alert preview and manifest prepared.');}];
    actions.forEach((action,i)=>timers.current.push(setTimeout(action,(i+1)*1400)));
  }
  function recover() {clearTimers();setRunning(false);setStep(-1);setMode('recovery');setAqi(ZONES[zone].aqi);setDeviceAqi(ZONES[zone].aqi);log('Sample ambient reading returned to baseline. Pod set to energy-saving mode.');}
  function exportManifest() {
    const manifest={project:'Atmos',dataSource:'local-simulation',timestamp:new Date().toISOString(),classroom:'4B',zone,aqi,pumpPercent:pump,lightPercent:light,carbonReduction:null,carbonReductionStatus:'not-measured',awsConnected:false,events};
    const url=URL.createObjectURL(new Blob([JSON.stringify(manifest,null,2)],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download='atmos-demo-manifest.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  return <div className="demo-console">
    <div className="console-top"><span><i className="status-dot"/> Control room</span><span className="simulation-label">Simulation</span></div>
    <div className="console-grid">
      <div className="telemetry"><div className="console-location"><div><span className="micro-label">City</span><label className="zone-select"><select aria-label="Monitoring city" value={zone} disabled={running} onChange={e=>{setZone(e.target.value);reset(e.target.value);}}>{Object.keys(ZONES).map(z=><option key={z}>{z}</option>)}</select><ChevronDown size={16}/></label></div><span className={'aqi-badge '+(aqi>200?'is-poor':'')}>{status}</span></div>
      <div className="aqi-reading"><span>{aqi}</span><div>India AQI</div><Activity size={38} strokeWidth={1}/></div>
      <div className="aqi-scale"><div className="aqi-marker" style={{left:(aqi/500*100)+'%'}}/></div><div className="scale-labels"><span>0 / GOOD</span><span>500 / SEVERE</span></div>
      <label className="scenario-slider">Adjust air quality <span>{aqi}</span><input type="range" min="0" max="500" value={aqi} disabled={running} onChange={e=>{setAqi(Number(e.target.value));setDeviceAqi(Number(e.target.value));setMode('custom');setStep(-1);}} aria-label="Simulated India AQI"/></label>
      <div className="device-metrics"><div><Wind size={18}/><span>Air agitation<strong>{pump}<small>%</small></strong></span></div><div><Lightbulb size={18}/><span>Growth light<strong>{light}<small>%</small></strong></span></div><div><Droplets size={18}/><span>Culture temp.<strong>24<small>°C</small></strong></span></div></div>
      <div className="demo-actions"><button className="button button-dark" disabled={running} onClick={trigger}><Play size={15} fill="currentColor"/>{running?'Running sequence…':'Simulate smog event'}<ArrowUpRight size={17}/></button><button className="reset-button" onClick={()=>reset()} aria-label="Reset demo"><RotateCcw size={18}/></button></div>
      <button className="text-button recover-button" onClick={recover} disabled={running||mode==='baseline'}>Return to clean-air baseline <span>↗</span></button>
      </div>
      <div className={'device-preview '+(deviceAqi>300?'accelerated':'')}><div className="device-preview-top"><span>Live pod preview</span><span><i className="status-dot"/>{deviceAqi>200?'ACCELERATED':'ECO MODE'}</span></div><div className="demo-pod" role="img" aria-label={'Animated bioreactor running at '+pump+' percent air agitation'}><DemoPod power={pump} reduced={reduced}/></div></div>
    </div>
    <div className="pipeline" aria-label="Simulated cloud response stages">{STAGES.map((stage,i)=><div key={stage} className={step>=i?'complete':''}><span>{step>=i?<Check size={13}/>:('0'+(i+1))}</span>{stage}{i<3&&<span className="pipeline-arrow">→</span>}</div>)}</div>
    <div className="alert-preview" aria-live="polite">{step===3?<><span className="alert-icon"><Check size={16}/></span><div><strong>Classroom 4B · Alert preview</strong><p>High AQI in {zone}. Pump set to {pump}%.</p></div></>:<><span className="alert-icon"><Activity size={16}/></span><div><strong>{running?'Following the response…':'Ready to respond.'}</strong><p>{running?'Reading → controls → alert.':'Simulate smog to start.'}</p></div></>}<button onClick={exportManifest} className="manifest-button"><Download size={15}/> Export manifest</button></div>
    {events.length>0&&<details className="event-log"><summary>View simulation activity <span>{events.length} events</span></summary><ol>{events.map((event,i)=><li key={event.time+i}><time>{event.time}</time>{event.message}</li>)}</ol></details>}
    <p className="console-note">Simulated data and controls. Hardware and AWS are not connected.</p>
  </div>;
}
