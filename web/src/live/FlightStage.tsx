import { useEffect, useRef, useState } from 'react';
import { createFlightRenderer, type FlightRenderer } from './flightRenderer';
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
  const [available, setAvailable] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeMs, setTimeMs] = useState(0);
  const [state, setState] = useState('Ready to load');

  useEffect(() => {
    const container = host.current!;
    try { renderer.current = createFlightRenderer(container); }
    catch { setAvailable(false); }
    const lost = (event: Event) => { event.preventDefault(); setPlaying(false); setAvailable(false); setState('Graphics unavailable'); };
    container.addEventListener('webglcontextlost', lost, true);
    return () => { container.removeEventListener('webglcontextlost', lost, true); request.current?.abort(); renderer.current?.dispose(); renderer.current = null; };
  }, []);

  useEffect(() => {
    const visibility = () => { if (document.hidden) { setPlaying(false); setState('Paused · tab hidden'); } };
    document.addEventListener('visibilitychange', visibility);
    return () => document.removeEventListener('visibilitychange', visibility);
  }, []);

  useEffect(() => {
    renderer.current?.draw(preview ? previewPose(preview, elapsed.current) : null, elapsed.current);
    if (!playing || !preview || !available) return;
    const start = performance.now() - elapsed.current;
    const duration = (preview.snapshots.length - 1) * preview.dt_ms;
    let frame = 0;
    const animate = (now: number) => {
      elapsed.current = Math.min(duration, Math.max(0, now - start));
      renderer.current?.draw(previewPose(preview, elapsed.current), elapsed.current);
      setTimeMs(elapsed.current);
      if (elapsed.current >= duration) { setPlaying(false); setState('Complete · frozen'); }
      else frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
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
  function freeze(label: string) { setPlaying(false); setState(label); }
  function reset() {
    freeze('Reset · idle'); elapsed.current = 0; setTimeMs(0);
    renderer.current?.draw(preview ? previewPose(preview, 0) : null, 0);
  }
  const pose = preview ? previewPose(preview, timeMs) : null;
  const completed = preview !== null && timeMs >= (preview.snapshots.length - 1) * preview.dt_ms;
  return <section className="flight-section" aria-labelledby="flight-heading">
    <div className="flight-heading"><h2 id="flight-heading">An open space for flight</h2><span className="flight-label">SYNTHETIC CONTROL REPLAY</span></div>
    <div className="flight-viewport">
      <div ref={host} className="flight-canvas" data-testid="flight-canvas" />
      <div className="flight-overlay"><span>FLIGHT STUDY / 003</span><span>LOCAL PROCEDURAL SCENE</span></div>
      {!available && <div className="flight-unavailable" role="status">3D view unavailable. WebGL2 is required. Playback is disabled; reload after enabling graphics.</div>}
      <div className="flight-caption">Original procedural fly · following spectator camera</div>
    </div>
    <div className="flight-controls">
      <button onClick={() => { void load(); }} disabled={loading || playing}>Load synthetic preview</button>
      <button disabled={!preview || playing || !available || completed} onClick={() => { if (!document.hidden) { setPlaying(true); setState('Playing synthetic replay'); } }}>Play synthetic preview</button>
      <button className="secondary" disabled={!playing} onClick={() => freeze('Paused · frozen')}>Pause</button>
      <button className="secondary" disabled={!preview} onClick={() => freeze('Stopped · frozen')}>Stop</button>
      <button className="secondary" disabled={!preview} onClick={reset}>Reset preview</button>
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
