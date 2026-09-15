import { useEffect, useState } from 'react';
import { parseLiveContract } from './contracts';
import type { LiveConfig } from './contracts';

export function Live() {
  const [config, setConfig] = useState<LiveConfig | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function read(path: string) {
      const response = await fetch(path, { method: 'GET', signal: controller.signal, cache: 'no-store' });
      if (!response.ok) throw new Error(`Local service returned HTTP ${response.status}.`);
      return response.json() as Promise<unknown>;
    }
    void Promise.all([read('/health/live'), read('/api/live/config')]).then(([health, settings]) => {
      parseLiveContract('LiveHealth', health);
      const checked = parseLiveContract('LiveConfig', settings);
      if (!controller.signal.aborted) setConfig(checked);
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Local service is unavailable.');
    });
    return () => controller.abort();
  }, []);

  return <div className="shell">
    <header className="masthead"><a className="wordmark" href="/live">FLYJAM <span>LIVE</span></a><span className="edition">LOCAL · OBS00</span></header>
    <main>
      <section className="intro"><p className="eyebrow">OBS TO FLIGHT</p><h1>Live foundation</h1>
        <p className="lede">Capture and inference are unavailable in OBS00. This page checks the local service and stays idle.</p></section>
      <section className="status-card" aria-labelledby="live-status-title">
        <h2 id="live-status-title">Local service</h2>
        {error ? <div role="alert" className="error"><p>{error}</p><p>Check that the live service is running, then reload this page.</p></div>
          : <p role="status" className="availability">{config ? 'Idle · foundation service available' : 'Checking local service…'}</p>}
        {config && <dl className="facts">
          <div><dt>Capture backend</dt><dd>{config.backend}</dd></div>
          <div><dt>Source</dt><dd>Explicit selection required</dd></div>
          <div><dt>Recording</dt><dd>Off by default</dd></div>
          <div><dt>Neural calls this page</dt><dd>0</dd></div>
        </dl>}
        <p className="context">Source selection and explicit preview arrive in OBS01. Select an approved OBS virtual device before any capture. No source is selected here.</p>
      </section>
    </main>
    <footer><span>Private local workspace</span><span>OBS00 · idle service and contracts</span></footer>
  </div>;
}
