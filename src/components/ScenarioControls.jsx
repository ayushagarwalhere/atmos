import { Cloud, CloudRain, Flame, RotateCcw, Wind, ArrowUpRight } from 'lucide-react';
import { SCENARIO_PRESETS } from '../scenarios';

const fmt=(value,digits=1)=>value==null?'—':Number(value).toFixed(digits);
const FIELD_LABELS={wind_speed_kmh:'Wind speed',wind_sin:'Wind direction',wind_cos:'Wind direction',upwind_fire_count:'Upwind fire activity',upwind_frp:'Upwind fire / emission proxy',rain_mm:'Rainfall',cloud_cover_pct:'Cloud cover',humidity_pct:'Humidity',temperature_c:'Temperature',boundary_layer_height:'Mixing height',recent_pm25:'Recent PM2.5',pm25_lag_3h:'PM2.5 three hours ago',pm25_lag_12h:'PM2.5 twelve hours ago'};
export const featureLabel=name=>FIELD_LABELS[name]||name.replaceAll('_',' ');

export function WeatherStrip({city}){
  const weather=city.weather?.effective||{};
  return <div className="weather-strip" aria-label="City weather inputs">
    <span><Wind size={14}/><b>{fmt(weather.speed_kmh)}</b><small>km/h wind</small></span>
    <span><CloudRain size={14}/><b>{fmt(weather.rain_mm)}</b><small>mm rain / hour</small></span>
    <span><Cloud size={14}/><b>{fmt(weather.cloud_cover_pct,0)}</b><small>% cloud</small></span>
  </div>;
}

function Slider({id,label,icon:Icon,value,min,max,step=1,unit,onChange,override,prefix=''}){
  return <div className="weather-slider"><label htmlFor={prefix+id}><span>{Icon&&<Icon size={15}/>} {label}</span><b>{fmt(value,step<1?1:0)}{unit}</b></label><input id={prefix+id} type="range" min={min} max={max} step={step} value={value} onChange={event=>onChange(Number(event.target.value))}/>{override&&<small>Scenario override</small>}</div>;
}

export default function ScenarioControls({city,values,onChange,onReset,onPreset,onTrain,mode,busy,showResults=true,idPrefix=''}){
  const weather=city.weather?.observed||{};
  const baseline=city.baseline_forecast?.pm25, alternative=city.forecast.pm25;
  const difference=city.scenario_difference;
  const field=(name,fallback)=>values[name]??weather[name]??fallback;
  return <div className="scenario-lab">
    <span className="micro-label">CHANGE THE CONDITIONS</span>
    <p className="scenario-intro">{showResults?'Compare a what-if with the same city, time and forecast horizon.':'Set your assumptions, then run the simulation to compare every city.'}</p>
    <div className="scenario-presets" aria-label="Scenario presets">
      <button onClick={()=>onPreset('calm')}><Flame size={13}/> Calm + burning</button>
      <button onClick={()=>onPreset('rain')}><CloudRain size={13}/> Rainy</button>
      <button onClick={()=>onPreset('wind')}><Wind size={13}/> Clear + windy</button>
    </div>
    <details className="more-scenarios"><summary>More what-if templates</summary><div className="scenario-presets">{['half','stop','shift','night','surge'].map(key=><button key={key} onClick={()=>onPreset(key)}>{SCENARIO_PRESETS[key].name}</button>)}</div></details>
    <Slider prefix={idPrefix} id="wind-range" label="Wind from direction" icon={Wind} min={0} max={360} value={values.direction??weather.direction_deg??310} unit="°" onChange={value=>onChange('direction',value)} override={values.direction!=null}/>
    <Slider prefix={idPrefix} id="speed-range" label="Wind speed" min={0} max={60} value={values.speed??weather.speed_kmh??18} unit=" km/h" onChange={value=>onChange('speed',value)} override={values.speed!=null}/>
    <Slider prefix={idPrefix} id="rain-range" label="Rainfall in one hour" icon={CloudRain} min={0} max={20} step={.5} value={field('rain_mm',0)} unit=" mm" onChange={value=>onChange('rain_mm',value)} override={values.rain_mm!=null}/>
    <Slider prefix={idPrefix} id="cloud-range" label="Cloud cover" icon={Cloud} min={0} max={100} value={field('cloud_cover_pct',50)} unit="%" onChange={value=>onChange('cloud_cover_pct',value)} override={values.cloud_cover_pct!=null}/>
    <Slider prefix={idPrefix} id="fire-range" label="Fire activity" icon={Flame} min={0} max={4} step={.1} value={values.multiplier} unit="×" onChange={value=>onChange('multiplier',value)}/>
    <label className="burning-select">Assumed burning source<select aria-label="Assumed burning source" value={values.burning} onChange={event=>onChange('burning',event.target.value)}><option value="unspecified">Unknown / satellite hotspot</option><option value="crop_residue">Crop residue burning</option><option value="wildfire">Vegetation / wildfire</option><option value="waste">Waste burning</option></select></label>
    <details className="weather-advanced"><summary>Emission and mixing assumptions</summary>
      <Slider prefix={idPrefix} id="smoke-range" label="Smoke emission proxy" min={0} max={3} step={.1} value={values.smoke_factor} unit="×" onChange={value=>onChange('smoke_factor',value)}/>
      <p>This scales the FRP input per detection. Fuel-specific emission factors are not available.</p>
      <Slider prefix={idPrefix} id="humidity-range" label="Relative humidity" min={0} max={100} value={field('humidity_pct',60)} unit="%" onChange={value=>onChange('humidity_pct',value)} override={values.humidity_pct!=null}/>
      <Slider prefix={idPrefix} id="mixing-range" label="Mixing height" min={50} max={3000} step={50} value={field('boundary_layer_height',500)} unit=" m" onChange={value=>onChange('boundary_layer_height',value)} override={values.boundary_layer_height!=null}/>
      <Slider prefix={idPrefix} id="temperature-range" label="Temperature" min={-10} max={50} value={field('temperature_c',25)} unit="°C" onChange={value=>onChange('temperature_c',value)} override={values.temperature_c!=null}/>
    </details>
    {showResults&&<div className="scenario-comparison" aria-live="polite"><span className="micro-label">PM2.5 COMPARISON · µg/m³</span><div><span>Baseline<strong>{fmt(baseline)}</strong></span><span>Scenario<strong>{fmt(alternative)}</strong></span></div><p className={difference>0?'difference-up':difference<0?'difference-down':''}>{difference==null?'Comparison unavailable':`${difference>0?'+':''}${fmt(difference)} µg/m³ versus baseline`}</p><small>{city.forecast.model} · +{city.forecast.horizon||6}h</small></div>}
    {showResults&&mode==='live'&&city.forecast.model==='persistence'&&<div className="scenario-model-notice"><p>The current forecast carries the latest station reading forward. Train a model to explore numerical weather and burning responses.</p><button disabled={busy} onClick={onTrain}>Train on real history <ArrowUpRight size={13}/></button></div>}
    <details className="weather-explanation" open><summary>Why the outlook can change</summary>{city.environment?.notes.map(note=><p key={note.factor}><b>{note.factor}</b>{note.text}</p>)}<small>{city.environment?.method}</small></details>
    <p className="scenario-note">{mode==='demo'?'Demo changes use a synthetic response recipe, not calibrated forecasts. Burning source is an assumption; it does not assign a fuel-specific emission factor.':'Scenario responses are exploratory. Their uncertainty intervals are uncalibrated.'}</p>
    <button className="underlined-link" onClick={onReset}>Use original feed inputs <RotateCcw size={14}/></button>
  </div>;
}
