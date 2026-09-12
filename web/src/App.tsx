import { useEffect, useState } from 'react';
import { parseCapabilities } from './contracts';
import type { Capabilities } from './generated/contracts';

type State = { kind: 'loading' } | { kind: 'ready'; capabilities: Capabilities } | { kind: 'error'; message: string };

export function App() {
  const [state, setState] = useState<State>({ kind: 'loading' });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const abort = new AbortController();
    setState({ kind: 'loading' });
    async function load() {
      try {
        const response = await fetch('/api/config', { signal: abort.signal, headers: { Accept: 'application/json' } });
        if (!response.ok) throw new Error('The simulation service is unavailable.');
        const capabilities = parseCapabilities(await response.json());
        if (!abort.signal.aborted) setState({ kind: 'ready', capabilities });
      } catch (error) {
        if (!abort.signal.aborted) setState({ kind: 'error', message: error instanceof Error ? error.message : 'The simulation service is unavailable.' });
      }
    }
    void load();
    return () => abort.abort();
  }, [attempt]);

  const capabilities = state.kind === 'ready' ? state.capabilities : null;
  return (
    <div className="shell">
      <header className="masthead"><a href="/" aria-label="FLYTRAP home" className="wordmark">FLYTRAP<span aria-hidden="true">↗</span></a><span className="edition">SIMULATION LAB / 01</span></header>
      {capabilities?.fixture && <div className="fixture-banner" role="note">FIXTURE — NOT REAL MODEL</div>}
      <main id="main">
        <div className="intro"><p className="eyebrow">CONNECTOME-BASED SIMULATION</p><h1>A small world.<br />An inspectable experiment.</h1><p className="lede">A foundation for visual challenges, model-driven movement, and recorded replays.</p></div>
        <section className="status-card" aria-labelledby="service-title">
          <div className="card-header"><h2 id="service-title">Service status</h2><span className="tag">FOUNDATION PREVIEW</span></div>
          {state.kind === 'loading' && <p role="status">Checking service capabilities…</p>}
          {state.kind === 'error' && <div className="error"><p role="alert">{state.message}</p><button onClick={() => setAttempt(attempt + 1)}>Retry connection</button></div>}
          {capabilities && <>
            <p className="availability" role="status"><span className="status-dot" aria-hidden="true" />{capabilities.real_model_available ? 'Real model available' : 'Real model unavailable'}</p>
            <dl className="facts">
              <div><dt>Runtime profile</dt><dd>{capabilities.fixture ? 'Synthetic fixture' : 'Real connectome'}</dd></div>
              <div><dt>Run admission</dt><dd>{capabilities.admission === 'closed' ? 'Closed' : capabilities.admission === 'open' ? 'Open' : 'Unavailable'}</dd></div>
              <div><dt>Learning evidence</dt><dd>{capabilities.learning_claim_status === 'NOT_RUN' ? 'Not evaluated' : capabilities.learning_claim_status.toLowerCase()}</dd></div>
              <div><dt>Contract version</dt><dd>{capabilities.schema_version}</dd></div>
            </dl>
            <p className="context">{capabilities.fixture ? 'This local profile checks the application foundation using synthetic data. It does not establish real-model behavior.' : 'Service capabilities are reported by the API. Real-model verification requires recorded execution evidence.'}</p>
          </>}
        </section>
        <aside className="method-note"><span className="note-index" aria-hidden="true">01 /</span><div><h2>Built to be inspected</h2><p>The planned controller receives visual pixels, explicit model state, and task-independent randomness. Challenge scoring belongs to the environment.</p></div></aside>
      </main>
      <footer><span>FLYTRAP · Local foundation</span><span>Learning claims require measured evidence.</span></footer>
    </div>
  );
}
