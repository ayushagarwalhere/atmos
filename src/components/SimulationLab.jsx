import { useEffect, useRef, useState } from 'react';
import { ArrowRight, Check, CloudRain, Copy, Download, Flame, History, Leaf, LoaderCircle, Moon, Play, RotateCcw, Save, Wind, X } from 'lucide-react';
import { api, downloadJSON } from '../api';
import { createSessionId, persistentSessionId } from '../session';
import { ORIGINAL_SCENARIO, SCENARIO_PRESETS, presetValues } from '../scenarios';
import ScenarioControls from './ScenarioControls';

const ICONS = { fire: Flame, rain: CloudRain, wind: Wind, leaf: Leaf, moon: Moon };
const fmt = value => value == null ? '—' : Number(value).toFixed(1);
const arrival = value => value == null ? 'No intersecting path' : `${value}h`;
const stamp = value => new Date(value).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
const selected = run => run?.comparisons.find(row => row.city_id === run.city_id);
const context = run => `${run.mode}|${run.city_id}|${run.horizon}|${run.at}`;
const loadSetups = () => { try { const data = JSON.parse(localStorage.getItem('atmos-scenario-setups') || '[]'); return Array.isArray(data) ? data.filter(item => item && typeof item.name === 'string' && item.values && [6,12,24].includes(item.horizon)).slice(0, 20) : []; } catch { return []; } };

function ComparisonBars({ row }) {
  const top = Math.max(1, row.baseline_pm25 || 0, row.scenario_pm25 || 0);
  return <div className="simulation-bars" aria-label="Baseline and scenario PM2.5">
    {[['Baseline', row.baseline_pm25], ['What-if', row.scenario_pm25]].map(([name, value]) => <div key={name}>
      <span>{name}</span><div><i style={{ width: `${value == null ? 0 : Math.max(2, value / top * 100)}%` }}/></div><b>{fmt(value)}</b>
    </div>)}
    <small>PM2.5 · µg/m³ · same inputs time and forecast horizon</small>
  </div>;
}

export default function SimulationLab({ mode, cityId, horizon, data, demoTrigger, onApply }) {
  const [sessionId] = useState(() => persistentSessionId('atmos-simulation-session'));
  const [template, setTemplate] = useState('surge');
  const [values, setValues] = useState(() => presetValues('surge'));
  const [name, setName] = useState(SCENARIO_PRESETS.surge.name);
  const [runHorizon, setRunHorizon] = useState(horizon);
  const [stage, setStage] = useState(0), [library, setLibrary] = useState('Templates');
  const [setups, setSetups] = useState(loadSetups), [runs, setRuns] = useState([]);
  const [result, setResult] = useState(null), [compared, setCompared] = useState([]);
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [notice, setNotice] = useState('');
  const [refresh, setRefresh] = useState(0);
  const request = useRef(), resultRef = useRef(), lastDemo = useRef(0);
  const city = data.cities.find(item => item.id === cityId);

  useEffect(() => {
    const controller = new AbortController();
    api(`/simulations?session_id=${sessionId}&mode=${mode}`, { signal: controller.signal })
      .then(next => setRuns(next.runs)).catch(err => { if (err.name !== 'AbortError') setError(err.message); });
    return () => controller.abort();
  }, [mode, sessionId, refresh]);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (!demoTrigger || demoTrigger === lastDemo.current || mode !== 'demo' || data.mode !== 'demo') return;
    lastDemo.current = demoTrigger;
    choose('half');
    run(presetValues('half'), SCENARIO_PRESETS.half.name);
  }, [demoTrigger, mode, data.mode]);

  function choose(key) {
    setTemplate(key); setValues(presetValues(key)); setName(SCENARIO_PRESETS[key].name); setStage(1); setNotice('');
  }
  async function run(inputs = values, title = name) {
    if (busy || !title.trim()) return;
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    setBusy(true); setError(''); setNotice(''); setStage(1);
    try {
      const next = await api('/simulations', { method: 'POST', signal: controller.signal,
        body: { name: title.trim(), session_id: sessionId, mode, city_id: cityId, horizon: runHorizon, at: data.time, ...inputs } });
      setResult(next); setStage(2); setRefresh(value => value + 1);
      onApply(next); resultRef.current?.scrollIntoView({ behavior: 'instant', block: 'nearest' });
    } catch (err) { if (err.name !== 'AbortError') setError(err.message); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  function saveSetup() {
    if (!name.trim()) return;
    const next = [{ id: createSessionId(), name: name.trim(), values: { ...values }, horizon: runHorizon, mode }, ...setups].slice(0, 20);
    try { localStorage.setItem('atmos-scenario-setups', JSON.stringify(next)); setSetups(next); setNotice('Setup saved in this browser.'); }
    catch { setError('Browser storage is unavailable. You can still download this setup.'); }
  }
  async function openRun(id) {
    if (busy) return;
    setError('');
    try { const next = await api(`/simulations/${id}?session_id=${sessionId}`); setResult(next); setStage(2); }
    catch (err) { setError(err.message); }
  }
  function addComparison() {
    if (!result || compared.some(item => item.id === result.id)) return;
    if (compared.length && context(compared[0]) !== context(result)) { setError('Compare runs for the same city, mode, forecast horizon and issue time. Clear this comparison to start another group.'); return; }
    if (compared.length >= 3) { setError('Compare up to three runs at once. Remove one to add another.'); return; }
    setCompared(previous => [...previous, result]); setNotice('Added to the comparison below.');
  }
  const row = selected(result);
  return <section className="simulation-lab" aria-label="What-if simulation lab">
    <div className="simulation-heading"><div><span className="micro-label">DESIGN A WHAT-IF</span><h3>Change the conditions.<br/><em>See the difference.</em></h3></div><span className="simulation-mode">{mode === 'demo' ? 'Synthetic demo' : 'Imported observations'} · {city.name}</span></div>
    <ol className="simulation-steps">{['Choose a template', 'Configure & run', 'Compare results'].map((text, index) => <li key={text} className={stage === index ? 'current' : stage > index ? 'done' : ''} aria-current={stage === index ? 'step' : undefined}><span>{stage > index ? <Check size={14}/> : index + 1}</span>{text}</li>)}</ol>
    {error && <div className="twin-message error" role="alert"><span>{error}</span><button onClick={() => setError('')}>Dismiss</button></div>}
    {notice && <div className="twin-message" role="status"><span>{notice}</span><button onClick={() => setNotice('')}>Dismiss</button></div>}
    <div className="simulation-builder">
      <div className="simulation-library">
        <div className="simulation-library-tabs" role="tablist" aria-label="Scenario library">{['Templates', 'Saved setups', 'Run history'].map(label => <button role="tab" aria-selected={library === label} key={label} onClick={() => setLibrary(label)}>{label}</button>)}</div>
        {library === 'Templates' && <div className="simulation-template-grid">{Object.entries(SCENARIO_PRESETS).map(([key, item]) => { const Icon = ICONS[item.icon]; return <button key={key} className={'simulation-template ' + (template === key ? 'selected' : '')} aria-pressed={template === key} onClick={() => choose(key)} disabled={busy}><div><Icon size={22}/><small>{item.category}</small>{template === key && <Check size={16}/>}</div><b>{item.name}</b><p>{item.description}</p><span>Configure <ArrowRight size={14}/></span></button>; })}</div>}
        {library === 'Saved setups' && <div className="simulation-saved">{setups.filter(item => item.mode === mode).length ? setups.filter(item => item.mode === mode).map(item => <article key={item.id}><div><b>{item.name}</b><small>+{item.horizon}h · saved in this browser</small></div><button disabled={busy} onClick={() => { setValues({ ...ORIGINAL_SCENARIO, ...item.values }); setName(item.name); setRunHorizon(item.horizon); setTemplate(null); setStage(1); }}>Load setup</button></article>) : <div className="empty-state"><Save/><p>Save a configuration to reuse its assumptions later.</p></div>}</div>}
        {library === 'Run history' && <div className="simulation-saved">{runs.length ? runs.map(item => <article key={item.id}><div><b>{item.name}</b><small>{item.city_id} · +{item.horizon}h · {stamp(item.created_at)}</small><span>{fmt(item.comparison.scenario_pm25)} µg/m³ · Δ {fmt(item.comparison.difference)}</span></div><button disabled={busy} onClick={() => openRun(item.id)}>View report</button></article>) : <div className="empty-state"><History/><p>Completed runs are saved on the server for this browser session.</p></div>}</div>}
        <div className="scenario-suggestion"><Wind size={20}/><div><b>Try a controlled comparison</b><p>Run a 50% burning reduction, then pause burning entirely. Keep the city, issue time and horizon unchanged.</p><button disabled={busy} onClick={() => choose('half')}>Use 50% reduction <ArrowRight size={14}/></button></div></div>
      </div>
      <div className="simulation-configuration"><span className="micro-label">YOUR SIMULATION</span><label>Scenario name<input maxLength={100} value={name} onChange={event => setName(event.target.value)} disabled={busy}/></label><div className="simulation-context"><span>{city.name}<small>Issue time {stamp(data.time)} IST</small></span><label>Outlook<select value={runHorizon} disabled={busy} onChange={event => setRunHorizon(Number(event.target.value))}>{[6, 12, 24].map(value => <option key={value} value={value}>+{value} hours</option>)}</select></label></div>
        <ScenarioControls city={city} mode={mode} values={values} busy={busy} showResults={false} idPrefix="sim-" onPreset={choose} onChange={(key, value) => { setTemplate(null); setValues(previous => ({ ...previous, [key]: value })); setStage(1); }} onReset={() => { setValues({ ...ORIGINAL_SCENARIO }); setTemplate(null); }}/>
        <div className="simulation-runbar"><button className="simulation-run" disabled={busy || !name.trim()} onClick={() => run()}>{busy ? <LoaderCircle className="spin" size={18}/> : <Play size={18}/>} {busy ? 'Calculating the what-if…' : 'Run simulation'}</button><button disabled={busy || !name.trim()} onClick={saveSetup} aria-label="Save scenario setup"><Save size={18}/></button><button disabled={busy} onClick={() => downloadJSON({ name, mode, city_id: cityId, horizon: runHorizon, inputs: values }, 'atmos-scenario-setup.json')} aria-label="Download scenario setup"><Download size={18}/></button></div>
        {busy && <p className="simulation-running" role="status">Calculating baseline, transport paths and city comparisons, then saving the result.</p>}
      </div>
    </div>
    <div ref={resultRef} className="simulation-results" aria-live="polite">
      {result && <><div className="simulation-result-title"><div><span className="micro-label">COMPLETED · {stamp(result.created_at)} IST</span><h4>{result.name}</h4><p>{result.city_id} · +{result.horizon}h · {result.note}</p></div><div><button onClick={addComparison}><Copy size={15}/> Compare this run</button><button onClick={() => onApply(result)}><ArrowRight size={15}/> Apply to map</button><button onClick={() => downloadJSON(result, `atmos-${result.id}.json`)}><Download size={15}/> Export report</button></div></div>
        <div className="simulation-result-grid"><ComparisonBars row={row}/><div className="simulation-impact"><span className="micro-label">WHAT CHANGED</span><strong className={row.difference > 0 ? 'difference-up' : row.difference < 0 ? 'difference-down' : ''}>{row.difference > 0 ? '+' : ''}{fmt(row.difference)} <small>µg/m³</small></strong><p>Arrival: {arrival(row.baseline_arrival)} → {arrival(row.scenario_arrival)}</p><p>Potentially intersecting schools: {result.impact.baseline.schools} → {result.impact.scenario.schools}</p><small>{result.impact.scenario.method}</small></div></div>
        <div className="simulation-table-wrap"><table className="simulation-regional-table"><caption>Regional comparison · PM2.5 in µg/m³</caption><thead><tr><th>City</th><th>Baseline</th><th>What-if</th><th>Change</th><th>Arrival</th></tr></thead><tbody>{result.comparisons.map(item => <tr key={item.city_id}><th>{item.name}</th><td>{fmt(item.baseline_pm25)}</td><td>{fmt(item.scenario_pm25)}</td><td className={item.difference > 0 ? 'difference-up' : item.difference < 0 ? 'difference-down' : ''}>{item.difference > 0 ? '+' : ''}{fmt(item.difference)}</td><td>{arrival(item.scenario_arrival)}</td></tr>)}</tbody></table></div>
        <details className="simulation-assumptions"><summary>Method, assumptions & saved inputs</summary><p>{result.scenario.cities.find(item => item.id === result.city_id)?.forecast.response_method || result.scenario.transport_method}</p><p>{result.cloud_delivery.detail || `Report delivery: ${result.cloud_delivery.status}`}</p><pre>{JSON.stringify(result.inputs, null, 2)}</pre></details></>}
    </div>
    {compared.length > 0 && <div className="simulation-compare"><div><h4>Compare saved runs</h4><button onClick={() => setCompared([])}>Clear comparison <RotateCcw size={14}/></button></div><p>Same city, issue time, mode and forecast horizon.</p><div className="simulation-table-wrap"><table><thead><tr><th>Scenario</th><th>Baseline</th><th>What-if</th><th>Change</th><th>Arrival</th><th/></tr></thead><tbody>{compared.map(item => { const r = selected(item); return <tr key={item.id}><th>{item.name}</th><td>{fmt(r.baseline_pm25)}</td><td>{fmt(r.scenario_pm25)}</td><td>{fmt(r.difference)}</td><td>{arrival(r.scenario_arrival)}</td><td><button aria-label={'Remove ' + item.name} onClick={() => setCompared(previous => previous.filter(run => run.id !== item.id))}><X size={15}/></button></td></tr>; })}</tbody></table></div></div>}
  </section>;
}
