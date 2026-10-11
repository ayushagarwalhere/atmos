import { useEffect, useRef, useState } from 'react';
import { Activity, ArrowUpRight, Check, Download, Search, Workflow, LoaderCircle } from 'lucide-react';
import { api, downloadJSON } from '../api';

const AGENTS=['intelligence','forecast','scenario','impact','strategy'];
const terminal=status=>['complete','failed','interrupted'].includes(status);
const stamp=value=>new Date(value).toLocaleString('en-IN',{timeZone:'Asia/Kolkata',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});

export default function MissionControl({mode,cityId,horizon,audience,scenario,reduced}) {
  const [sessionId]=useState(()=>{let id=localStorage.getItem('atmos-analysis-session');if(!id){id=crypto.randomUUID();localStorage.setItem('atmos-analysis-session',id)}return id});
  const [run,setRun]=useState(null),[runs,setRuns]=useState([]),[events,setEvents]=useState([]);
  const [artifacts,setArtifacts]=useState([]),[actions,setActions]=useState([]),[platform,setPlatform]=useState(null);
  const [query,setQuery]=useState(''),[matches,setMatches]=useState(null),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const [submitting,setSubmitting]=useState(false),[refresh,setRefresh]=useState(0),[tab,setTab]=useState('Workflow');
  const stream=useRef();
  const active=run&&!terminal(run.status);
  useEffect(()=>{
    let cancelled=false;
    Promise.all([api('/runs?session_id='+sessionId),api('/artifacts?mode='+mode),api('/actions?mode='+mode),api('/health')]).then(([history,library,plans,health])=>{
      if(cancelled)return;setRuns(history.runs);setArtifacts(library.artifacts);setActions(plans.actions);setPlatform(health.platform);
    }).catch(err=>{if(!cancelled)setError(err.message)});
    return()=>{cancelled=true};
  },[mode,sessionId,refresh]);
  useEffect(()=>{
    if(!run||terminal(run.status))return;
    const source=new EventSource(`/api/runs/${run.id}/events`);stream.current=source;
    source.onmessage=async message=>{
      const event=JSON.parse(message.data);
      setEvents(previous=>previous.some(item=>item.sequence===event.sequence)?previous:[...previous,event]);
      if(['complete','failed','interrupted'].includes(event.kind)){
        source.close();
        try{setRun(await api('/runs/'+run.id));setRefresh(value=>value+1)}catch(err){setError(err.message)}
      }
    };
    source.onerror=()=>{setNotice('Event connection interrupted; inspect the saved run or reconnect.');source.close()};
    return()=>source.close();
  },[run?.id,run?.status]);
  useEffect(()=>{
    if(!active)return;
    const timer=setInterval(async()=>{
      try{const current=await api('/runs/'+run.id);if(terminal(current.status)){setRun(current);setRefresh(value=>value+1)}}catch{/* The event stream and saved-run controls remain available. */}
    },3000);
    return()=>clearInterval(timer);
  },[active,run?.id]);
  async function launch(){
    setSubmitting(true);setError('');setNotice('');setEvents([]);
    try{
      const next=await api('/analysis',{method:'POST',body:{mode,city_id:cityId,horizon,audience,session_id:sessionId,...scenario}});
      setRun(next);setRefresh(value=>value+1);
    }catch(err){setError(err.message)}finally{setSubmitting(false)}
  }
  async function inspect(id){
    stream.current?.close();
    try{setRun(await api('/runs/'+id));setEvents([]);setError('')}catch(err){setError(err.message)}
  }
  async function changeAction(id,status){
    try{await api('/actions/'+id,{method:'PATCH',body:{status}});setRefresh(value=>value+1)}catch(err){setError(err.message)}
  }
  async function search(event){
    event.preventDefault();setError('');
    try{setMatches(await api(`/evidence/search?mode=${mode}&city_id=${cityId}&q=${encodeURIComponent(query)}`))}catch(err){setError(err.message)}
  }
  async function exportArtifact(id){
    try{downloadJSON(await api('/artifacts/'+id),'atmos-analysis-'+id+'.json')}catch(err){setError(err.message)}
  }
  async function serviceAction(path,method='POST'){
    try{const result=await api(path,{method});setNotice(result.id?`Job ${result.id} started. Inspect its status in API /api/jobs/${result.id}.`:JSON.stringify(result))}catch(err){setError(err.message)}
  }
  const evidence=run?.result?.agents;
  return <section className={'mission-control '+(reduced?'motion-paused':'')} aria-label="Analysis workspace">
    <div className="workspace-heading"><div><span className="micro-label">CONNECTED SPECIALISTS · PERSISTENT EVIDENCE</span><h3>From signals to a plan.</h3></div><Workflow size={25}/></div>
    <div className="mission-toolbar"><p>Run all five specialists for {cityId.charAt(0).toUpperCase()+cityId.slice(1)}. Compare the current outlook with your scenario and keep an inspectable record.</p><button className="button button-dark" disabled={submitting||active} onClick={launch}>{submitting||active?<LoaderCircle className="spin" size={17}/>:<Activity size={17}/>} {active?'Analysis running':'Run city analysis'} <ArrowUpRight size={15}/></button></div>
    <div className="mission-tabs" role="tablist" aria-label="Analysis workspace views">{['Workflow','Evidence library','Action plan'].map(name=><button key={name} role="tab" aria-selected={tab===name} onClick={()=>setTab(name)}>{name}</button>)}</div>
    {error&&<p className="twin-message error" role="alert">{error}</p>}{notice&&<p className="twin-message">{notice}</p>}
    {tab==='Workflow'&&<div className="mission-grid">
      <div><div className="specialist-graph">{AGENTS.map((name,index)=>{
        const complete=events.some(event=>event.kind==='tool_completed'&&event.payload.agent===name)||Boolean(evidence?.[name]);
        const running=!complete&&events.some(event=>event.kind==='tool_started'&&event.payload.agent===name);
        return <div key={name} className={'specialist-node '+(complete?'complete':running?'running':'')}><span className="specialist-status">{complete?<Check size={15}/>:running?<LoaderCircle size={15} className="spin"/>:String(index+1).padStart(2,'0')}</span><b>{name}</b><small>{complete?'Evidence collected':running?'Calling tools':'Awaiting analysis'}</small>{index<4&&<span className="specialist-link" aria-hidden="true">↓</span>}</div>
      })}</div>{run&&<div className="run-summary"><b>{run.status.toUpperCase()} · {run.mode==='demo'?'SYNTHETIC':'LIVE INPUTS'}</b><p>{run.error||run.result?.agents.strategy.advisory||'The graph is collecting authoritative tool evidence.'}</p>{run.result&&<><span>{(run.result.duration_ms/1000).toFixed(2)}s · AWS Strands Graph · {run.result.provider}</span><div className="validation-actions"><button onClick={()=>downloadJSON(run,'atmos-run.json')}>Export run <Download size={14}/></button><button onClick={()=>inspect(run.id)}>Refresh saved run</button></div><details><summary>Inspect all specialist outputs</summary><pre>{JSON.stringify(run.result,null,2)}</pre></details></>}</div>}
      {events.length>0&&<details className="execution-events" open><summary>Execution events</summary>{events.map(event=><div key={event.sequence}><span>{event.kind.replaceAll('_',' ')}</span><b>{event.payload.agent||event.payload.framework||''}</b><small>{stamp(event.time)}{event.payload.duration_ms!=null?` · ${event.payload.duration_ms} ms`:''}</small></div>)}</details>}</div>
      <div className="run-history"><span className="micro-label">THIS SESSION</span><h4>Saved analyses</h4>{runs.length?runs.slice(0,12).map(item=><button key={item.id} className={run?.id===item.id?'selected':''} onClick={()=>inspect(item.id)} disabled={Boolean(active&&item.id!==run?.id)}><b>{item.city_id} · {item.mode}</b><span>{stamp(item.created_at)} · {item.status}</span></button>):<p>No analyses yet. Runs and their evidence survive a backend restart.</p>}<small>Forecast evidence is pinned to the run time. Saved results are not current observations.</small></div>
    </div>}
    {tab==='Evidence library'&&<div className="evidence-library"><form className="evidence-search" onSubmit={search}><Search size={18}/><input aria-label="Search saved evidence" placeholder="Search this city’s saved evidence…" value={query} onChange={event=>setQuery(event.target.value)}/><button disabled={!query.trim()}>Search</button></form>{matches&&<div className="search-results"><small>{matches.engine}{matches.error?` · ${matches.error}`:''}</small>{matches.results.length?matches.results.map(item=><article key={item.id}><b>{item.title}</b><p>{item.excerpt}</p><button onClick={()=>exportArtifact(item.id)}>Open evidence <Download size={14}/></button></article>):<p>No matching saved evidence in this data mode.</p>}</div>}<div className="artifact-list">{artifacts.length?artifacts.map(item=><article key={item.id}><div><b>{item.title}</b><span>{stamp(item.time)} · {item.delivery}</span></div><button onClick={()=>exportArtifact(item.id)} aria-label={'Export '+item.title}><Download size={17}/></button></article>):<p>Complete an analysis to add evidence to the library.</p>}</div></div>}
    {tab==='Action plan'&&<div className="action-board"><p>Track screening and verification steps locally. Updating a status records your decision; it does not contact a school or issue an advisory.</p>{actions.length?actions.map(item=><article key={item.id}><div><small>{item.city_id} · {item.mode==='demo'?'synthetic plan':'live evidence'} · {item.payload.audience}</small><b>{item.title}</b><p>{item.payload.reason}</p></div><select aria-label={'Status for '+item.title} value={item.status} onChange={event=>changeAction(item.id,event.target.value)}>{['proposed','accepted','in_progress','done','dismissed'].map(value=><option key={value} value={value}>{value.replaceAll('_',' ')}</option>)}</select></article>):<p>No proposed steps yet. Run the specialist workflow to create a grounded plan.</p>}</div>}
    <details className="build-it-runtime"><summary>AWS Build It runtime & audit</summary><p>AWS Strands runs the orchestrator and specialist graph. Choose Bedrock with your AWS profile or Ollama for language-model reasoning; the default provider is a deterministic rule router.</p><div className="runtime-services"><span>Strands <b>Integrated</b></span><span>OpenSearch <b>{platform?.opensearch_configured?'Configured':'Optional · not configured'}</b></span><span>S3 / DynamoDB <b>{platform?.aws_configured?`${platform.service_mode} configured`:'Optional · not configured'}</b></span><span>SQS <b>{platform?.queue_enabled?'Queue selected':'Local thread executor'}</b></span></div><p>{platform?.service_mode==='aws'?`Profile ${platform.profile} · region ${platform.region}. Cloud writes are ${platform.writes_enabled?'enabled':'off'}.`:'Configure an AWS profile and resource names for real AWS services, or select a local emulator.'} Configuration alone does not confirm a connection. SAM supplies a separate local artifact-manifest function.</p><div className="validation-actions"><button disabled={!platform?.aws_configured} onClick={()=>serviceAction('/aws/check','GET')}>Check AWS connection</button><button disabled={platform?.service_mode!=='local'} onClick={()=>serviceAction('/aws/bootstrap')}>Initialize emulator resources</button><button disabled={!platform?.queue_enabled} onClick={()=>serviceAction('/aws/queue/process')}>Process one queued analysis</button><button disabled={!platform?.opensearch_configured} onClick={()=>serviceAction('/search/index')}>Index library in OpenSearch</button><button onClick={async()=>{try{downloadJSON(await api('/audit'),'atmos-audit.json')}catch(err){setError(err.message)}}}>Export audit <Download size={14}/></button></div></details>
  </section>;
}
