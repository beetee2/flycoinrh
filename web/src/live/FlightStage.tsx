import { useEffect, useRef, useState } from 'react';
import { createFlightRenderer, FlightGraphicsError, type FlightRenderer } from './flightRenderer';
import { parseFlightPreview, previewPose, type FlightPreview } from './flightPreview';
import './flight.css';
import threeLicenseUrl from './three-LICENSE.txt?url&no-inline';

export function FlightStage() {
  const host = useRef<HTMLDivElement>(null);
  const renderer = useRef<FlightRenderer | null>(null);
  const request = useRef<AbortController | null>(null);
  const elapsed = useRef(0);
  const [preview, setPreview] = useState<FlightPreview | null>(null);
  const [playing, setPlaying] = useState(false);
  const [graphics, setGraphics] = useState('Initializing');
  const [graphicsErrors, setGraphicsErrors] = useState<string[]>([]);
  const [graphicsAttempt, setGraphicsAttempt] = useState(0);
  const retries = useRef(0);
  const frame = useRef(0);
  const available = graphics === 'Ready';
  function stopAnimation() { cancelAnimationFrame(frame.current); frame.current = 0; }
  function graphicsFailed(cause: unknown) {
    stopAnimation(); setPlaying(false); setState('Paused · graphics unavailable');
    const error = cause instanceof FlightGraphicsError ? cause : new FlightGraphicsError('renderer', cause);
    const label = error.kind === 'context-creation' ? 'Context creation failed' : error.kind === 'context-lost' ? 'Context lost' : 'Renderer failed';
    setGraphics(label);
    setGraphicsErrors(history => [...history, `${label}: ${error.message}`].slice(-4));
    const previous = renderer.current; renderer.current = null; previous?.dispose();
  }
  function draw(pose: Parameters<FlightRenderer['draw']>[0], ms: number) {
    if (!renderer.current) return false;
    try { renderer.current.draw(pose, ms); return true; }
    catch (error) { graphicsFailed(error); return false; }
  }
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeMs, setTimeMs] = useState(0);
  const [state, setState] = useState('Ready to load');

  useEffect(() => {
    let active = true;
    try {
      renderer.current = createFlightRenderer(host.current!, error => { if (active) graphicsFailed(error); });
      if (draw(preview ? previewPose(preview, elapsed.current) : null, elapsed.current)) {
        setGraphics('Ready');
        if (graphicsAttempt > 0) setState('Paused · graphics restored');
      }
    } catch (error) { graphicsFailed(error); }
    return () => {
      active = false; stopAnimation();
      const previous = renderer.current; renderer.current = null; previous?.dispose();
    };
    // Initialization is explicitly bounded by mount or Retry, independent of data/playback changes.
  }, [graphicsAttempt]);

  useEffect(() => () => { request.current?.abort(); }, []);

  useEffect(() => {
    const visibility = () => { if (document.hidden) { stopAnimation(); setPlaying(false); setState('Paused · tab hidden'); } };
    document.addEventListener('visibilitychange', visibility);
    return () => document.removeEventListener('visibilitychange', visibility);
  }, []);

  useEffect(() => {
    if (!draw(preview ? previewPose(preview, elapsed.current) : null, elapsed.current)) return;
    if (!playing || !preview || !available) return;
    const start = performance.now() - elapsed.current;
    const duration = (preview.snapshots.length - 1) * preview.dt_ms;
    const animate = (now: number) => {
      const nextTime = Math.min(duration, Math.max(0, now - start));
      if (!draw(previewPose(preview, nextTime), nextTime)) return;
      elapsed.current = nextTime; setTimeMs(nextTime);
      if (elapsed.current >= duration) { setPlaying(false); setState('Complete · frozen'); }
      else frame.current = requestAnimationFrame(animate);
    };
    frame.current = requestAnimationFrame(animate);
    return stopAnimation;
  }, [preview, playing, available]);

  async function load() {
    setPlaying(false); setLoading(true); setError(null); setState('Loading synthetic snapshots');
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    try {
      const response = await fetch('/api/live/flight-preview', { method: 'GET', cache: 'no-store', signal: controller.signal });
      if (!response.ok) throw new Error(`Preview service returned HTTP ${response.status}.`);
      const checked = parseFlightPreview(await response.json());
      if (controller.signal.aborted) return;
      elapsed.current = 0; setTimeMs(0); setPreview(checked); setState('Loaded · idle');
    } catch (cause) {
      if (!controller.signal.aborted) { setPreview(null); setError(cause instanceof Error ? cause.message : 'Preview unavailable.'); setState('Unavailable'); }
    } finally { if (!controller.signal.aborted) setLoading(false); }
  }
  function freeze(label: string) { stopAnimation(); setPlaying(false); setState(label); }
  function reset() {
    freeze('Reset · idle'); elapsed.current = 0; setTimeMs(0);
    draw(preview ? previewPose(preview, 0) : null, 0);
  }
  function retryGraphics() {
    if (retries.current >= 3 || available) return;
    retries.current += 1;
    stopAnimation(); setPlaying(false); setGraphics('Initializing');
    setGraphicsAttempt(retries.current);
  }
  const pose = preview ? previewPose(preview, timeMs) : null;
  const completed = preview !== null && timeMs >= (preview.snapshots.length - 1) * preview.dt_ms;
  return <section className="flight-section" aria-labelledby="flight-heading">
    <div className="flight-heading"><h2 id="flight-heading">An open space for flight</h2><span className="flight-label">SYNTHETIC CONTROL REPLAY</span></div>
    <div className="flight-viewport">
      <div ref={host} className="flight-canvas" data-testid="flight-canvas" />
      <div className="flight-overlay"><span>FLIGHT STUDY / 003</span><span>LOCAL PROCEDURAL SCENE</span></div>
      {!available && <div className="flight-unavailable" role="status">3D view unavailable. {graphics === 'Context creation failed' ? 'The browser could not create a WebGL2 context.' : graphics === 'Context lost' ? 'The browser lost the graphics context.' : graphics === 'Initializing' ? 'Initializing graphics.' : 'Renderer or scene initialization failed.'} Playback is disabled.</div>}
      <div className="flight-caption">Original procedural fly · following spectator camera</div>
    </div>
    <div className="flight-controls">
      <button onClick={() => { void load(); }} disabled={loading || playing}>Load synthetic preview</button>
      <button disabled={!preview || playing || !available || completed} onClick={() => { if (!document.hidden) { setPlaying(true); setState('Playing synthetic replay'); } }}>Play synthetic preview</button>
      <button className="secondary" disabled={!playing} onClick={() => freeze('Paused · frozen')}>Pause</button>
      <button className="secondary" disabled={!preview} onClick={() => freeze('Stopped · frozen')}>Stop</button>
      <button className="secondary" disabled={!preview} onClick={reset}>Reset preview</button>
    </div>
    <div className="flight-graphics">
      <p>Graphics: <strong data-testid="graphics-state">{graphics}</strong> · Preview data: <strong data-testid="preview-data-state">{loading ? 'Loading' : preview ? 'Loaded' : 'Not loaded'}</strong></p>
      {!available && <button className="secondary" onClick={retryGraphics} disabled={graphics === 'Initializing' || graphicsAttempt >= 3}>Retry graphics</button>}
      {!available && <p>{graphicsAttempt >= 3 ? 'Three retries used. Reload the page for another attempt.' : 'Retry makes one graphics attempt and keeps playback stopped. Up to three retries per page.'}</p>}
      {graphicsErrors.length > 0 && <details><summary>Graphics diagnostics (local to this page)</summary>
        <pre data-testid="graphics-details">{graphicsErrors.join('\n')}</pre>
        <p>These messages do not identify the cause. Browser GPU diagnostics may provide more detail.</p>
      </details>}
    </div>
    {error && <p role="alert" className="error">{error}</p>}
    <div className="flight-telemetry" aria-label="Synthetic replay telemetry">
      <p><span>PREVIEW STATE</span><strong data-testid="preview-state">{state}</strong></p>
      <p><span>SERVER TICK · 20 MS</span><strong data-testid="flight-tick">{pose?.tick ?? '—'}</strong></p>
      <p><span>POSITION · WORLD UNITS</span><strong data-testid="flight-position">{pose ? pose.position.map(value => value.toFixed(2)).join(' / ') : '—'}</strong></p>
    </div>
    <p className="flight-explanation">A fixed synthetic control sequence, computed by the server’s flight physics. This is a visual development preview; real neural output is not connected to this stage. The browser interpolates saved poses. Wing motion is decorative. Pause and Stop freeze travel; Reset returns to the first pose. Built with locally bundled <a href={threeLicenseUrl}>three.js (MIT)</a>.</p>
  </section>;
}
