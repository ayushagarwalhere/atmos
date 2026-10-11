import { useState } from 'react';
import { Cloud, Download, LoaderCircle, RefreshCw } from 'lucide-react';
import { api } from '../api';

const LABELS = { active: 'Active on AWS', integrated: 'SDK integrated', connected: 'Connected', configured: 'Configured · unchecked', not_configured: 'Awaiting setup', not_enabled: 'Not enabled', template_ready: 'Template ready', provisioned: 'Provisioned', local: 'Local environment' };

export default function AwsServicesPanel({ platform, onRefresh }) {
  const [busy, setBusy] = useState(false), [result, setResult] = useState(null), [error, setError] = useState('');
  async function check() {
    setBusy(true); setError('');
    try { setResult(await api('/aws/check')); onRefresh(); } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <section className="aws-services-panel" aria-label="AWS services used by Atmos">
    <div className="workspace-heading"><div><span className="micro-label">HOSTING, STORAGE & EXECUTION</span><h3>What runs on AWS.</h3></div><Cloud size={27}/></div>
    <p>Active services are separated from integrations that still need configuration. The Strands SDK runs in the application; it is not a hosted AWS service.</p>
    <div className="aws-service-grid">{platform?.inventory?.map(service => <article key={service.name}><div><span className={'aws-service-state ' + service.status}>{LABELS[service.status] || service.status}</span><small>{service.kind}</small></div><h4>{service.name}</h4><p>{service.purpose}</p></article>)}</div>
    <div className="aws-service-actions"><button disabled={busy || !platform?.aws_configured} onClick={check}>{busy ? <LoaderCircle size={16} className="spin"/> : <RefreshCw size={16}/>} Check cloud connections</button><a href="/api/aws/template" download="atmos-cloud.yaml"><Download size={16}/> Download infrastructure template</a></div>
    {!platform?.aws_configured && <p className="aws-service-note">Hosting is live on EC2. Additional data services need a provisioned stack and an EC2 application role. Reports currently remain on the persistent EC2 volume.</p>}
    {error && <p className="twin-message error" role="alert">{error}</p>}
    {result && <div className="aws-check-results" role="status">{Object.entries(result.checks).map(([name, check]) => <span key={name}><b>{name}</b> {check.status}{check.error ? ` · ${check.error}` : ''}</span>)}</div>}
  </section>;
}
