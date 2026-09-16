import { useEffect, useRef, useState } from 'react';
import { createFlightRenderer, FlightGraphicsError, type FlightRenderer } from './flightRenderer';
import { interpolatePose, parseFlightPreview, previewPose, type FlightPreview } from './flightPreview';
import type { FlightSnapshot } from './contracts';
import './flight.css';
import { DEFAULT_PRESENTATION_SETTINGS } from './presentationSettings';
import { PresentationPanel } from './PresentationPanel';
import threeLicenseUrl from './three-LICENSE.txt?url&no-inline';

export type StageMode = 'synthetic' | 'preview' | 'live' | 'replay';
type Props = { mode?: StageMode; modelMode?: 'real' | 'fixture' | 'none'; snapshot?: FlightSnapshot | null; motionAllowed?: boolean; freezePose?: boolean;
  backdropUrl?: string | null; backdropLabel?: string; onStop?: () => void; sessionActive?: boolean; historyKey?: string;
  onGraphicsFailure?: () => void; onGraphicsReady?: (ready: boolean) => void; onRenderingRate?: (hz: number) => void };
export function FlightStage({ mode = 'synthetic', modelMode = 'none', snapshot = null, motionAllowed = false, freezePose = false,
  onGraphicsFailure, onGraphicsReady, onRenderingRate, backdropUrl = null, backdropLabel = 'Source unavailable', onStop, sessionActive = false, historyKey = '' }: Props) {
  const [presentation, setPresentation] = useState<'screen-gremlin' | 'legacy'>('screen-gremlin');
  const [settings, setSettings] = useState({ ...DEFAULT_PRESENTATION_SETTINGS });
  const [clean, setClean] = useState(false);
  const [demoBackground, setDemoBackground] = useState('busy');
  const callbacks = useRef({ onGraphicsFailure, onGraphicsReady, onRenderingRate });
  callbacks.current = { onGraphicsFailure, onGraphicsReady, onRenderingRate };
  const displayed = useRef<FlightSnapshot | null>(null);
  const [rendered, setRendered] = useState<FlightSnapshot | null>(null);
  const stats = useRef({ start: performance.now(), count: 0 });
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
    callbacks.current.onGraphicsReady?.(false); callbacks.current.onGraphicsFailure?.();
    const error = cause instanceof FlightGraphicsError ? cause : new FlightGraphicsError('renderer', cause);
    const label = error.kind === 'context-creation' ? 'Context creation failed' : error.kind === 'context-lost' ? 'Context lost' : 'Renderer failed';
    setGraphics(label);
    setGraphicsErrors(history => [...history, `${label}: ${error.message}`].slice(-4));
    const previous = renderer.current; renderer.current = null; previous?.dispose();
  }
  function draw(pose: Parameters<FlightRenderer['draw']>[0], ms: number) {
    if (!renderer.current) return false;
    try {
      renderer.current.draw(pose, ms); displayed.current = pose; setRendered(pose);
      stats.current.count++;
      return true;
    }
    catch (error) { graphicsFailed(error); return false; }
  }
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeMs, setTimeMs] = useState(0);
  const [state, setState] = useState('Ready to load');

  useEffect(() => {
    let active = true;
    try {
      renderer.current = createFlightRenderer(host.current!, error => { if (active) graphicsFailed(error); }, { presentation, settings });
      if (draw(mode === 'synthetic' ? (preview ? previewPose(preview, elapsed.current) : null) : displayed.current, elapsed.current)) {
        setGraphics('Ready'); callbacks.current.onGraphicsReady?.(true);
        if (graphicsAttempt > 0) setState('Paused · graphics restored');
      }
    } catch (error) { graphicsFailed(error); }
    return () => {
      active = false; stopAnimation();
      const previous = renderer.current; renderer.current = null; previous?.dispose();
    };
    // Initialization is explicitly bounded by mount or Retry, independent of data/playback changes.
  }, [graphicsAttempt, presentation]);

  useEffect(() => { renderer.current?.updateSettings?.(settings); }, [settings]);
  useEffect(() => { renderer.current?.resetHistory?.(); }, [mode, historyKey]);

  useEffect(() => {
    const timer = setInterval(() => {
      const now = performance.now();
      callbacks.current.onRenderingRate?.(stats.current.count * 1000 / Math.max(1, now - stats.current.start));
      stats.current = { start: now, count: 0 };
    }, 500);
    return () => { clearInterval(timer); request.current?.abort(); };
  }, []);

  useEffect(() => {
    const visibility = () => { if (document.hidden) { stopAnimation(); setPlaying(false); setState('Paused · tab hidden'); } };
    document.addEventListener('visibilitychange', visibility);
    return () => document.removeEventListener('visibilitychange', visibility);
  }, []);

  useEffect(() => {
    if (mode !== 'synthetic') return;
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
  }, [preview, playing, available, mode]);

  useEffect(() => {
    if (mode === 'synthetic') return;
    stopAnimation(); setPlaying(false);
    if (!available) return;
    if (!snapshot) { draw(null, 0); return; }
    const previous = displayed.current;
    const sameSession = previous?.session_id === snapshot.session_id && previous?.generation === snapshot.generation;
    if (!sameSession || !motionAllowed || snapshot.neutral || document.hidden) {
      // Loss of ownership freezes the last displayed pose immediately. A terminal
      // authoritative pose is shown only when supplied with an explicit replay seek.
      if ((!freezePose && snapshot.neutral) || mode === 'replay' || !sameSession) draw(snapshot, snapshot.tick * 20);
      return;
    }
    const start = performance.now();
    const animate = (now: number) => {
      if (document.hidden) return;
      const blend = Math.min(1, Math.max(0, (now - start) / 100));
      if (!draw(interpolatePose(previous!, snapshot, blend), snapshot.tick * 20)) return;
      if (blend < 1) frame.current = requestAnimationFrame(animate);

    };
    frame.current = requestAnimationFrame(animate);
    return stopAnimation;
  }, [mode, snapshot, motionAllowed, freezePose, available]);

  async function load() {
    setPlaying(false); setLoading(true); setError(null); setState('Loading synthetic snapshots');
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    try {
      const response = await fetch('/api/live/flight-preview', { method: 'GET', cache: 'no-store', signal: controller.signal });
      if (!response.ok) throw new Error(`Preview service returned HTTP ${response.status}.`);
      const checked = parseFlightPreview(await response.json());
      if (controller.signal.aborted) return;
      renderer.current?.resetHistory?.(); elapsed.current = 0; setTimeMs(0); setPreview(checked); setState('Loaded · idle');
    } catch (cause) {
      if (!controller.signal.aborted) { setPreview(null); setError(cause instanceof Error ? cause.message : 'Preview unavailable.'); setState('Unavailable'); }
    } finally { if (!controller.signal.aborted) setLoading(false); }
  }
  function freeze(label: string) { stopAnimation(); setPlaying(false); setState(label); }
  function reset() {
    renderer.current?.resetHistory?.(); freeze('Reset · idle'); elapsed.current = 0; setTimeMs(0);
    draw(preview ? previewPose(preview, 0) : null, 0);
  }
  function retryGraphics() {
    if (retries.current >= 3 || available) return;
    retries.current += 1;
    stopAnimation(); setPlaying(false); setGraphics('Initializing');
    setGraphicsAttempt(retries.current);
  }
  const pose = mode === 'synthetic' ? (preview ? previewPose(preview, timeMs) : null) : rendered;
  const completed = preview !== null && timeMs >= (preview.snapshots.length - 1) * preview.dt_ms;
  const illustrative = mode === 'synthetic' || mode === 'replay';
  const imageUrl = illustrative ? `/sg01/${demoBackground}.svg` : backdropUrl;
  const imageLabel = mode === 'synthetic' ? 'ILLUSTRATIVE DEMO · ORIGINAL GENERATED ART' : mode === 'replay' ? 'ORIGINAL COLOR BACKDROP UNAVAILABLE · ILLUSTRATION' : backdropLabel;
  const actualMode = mode === 'synthetic' ? playing ? 'synthetic' : 'synthetic · paused' : mode === 'replay' ? motionAllowed ? 'replay' : 'replay · paused' : !motionAllowed ? mode === 'preview' && sessionActive ? 'preview · no inference' : 'paused' : modelMode === 'fixture' ? 'synthetic · fixture' : 'live';
  return <section className={`flight-section ${clean ? 'clean-view' : ''} presentation-${presentation}`} aria-labelledby="flight-heading">
    <div className="flight-heading"><div><h2 id="flight-heading">Meet Jam.</h2><span className="flight-label">{mode === 'synthetic' ? 'SYNTHETIC CONTROL REPLAY' : mode === 'preview' ? 'CAPTURE-ONLY PREVIEW' : mode === 'replay' ? 'RECORDED PLAYBACK' : modelMode === 'fixture' ? 'FIXTURE NEURAL SESSION' : 'NEURAL-DRIVEN LIVE FLIGHT'}</span></div>
      <div className="view-actions"><label>Presentation<select aria-label="Presentation" disabled={!available} value={presentation} onChange={e => { if (!available) return; freeze('Paused · presentation changed'); setPresentation(e.target.value as 'screen-gremlin' | 'legacy'); }}><option value="screen-gremlin">Screen Gremlin</option><option value="legacy">Legacy</option></select></label><button onClick={() => setClean(!clean)}>{clean ? 'Exit clean view' : 'Clean view'}</button>{sessionActive && clean && <button className="urgent-stop" onClick={onStop}>Stop session</button>}</div>
    </div>
    <div className={`flight-viewport ratio-${settings.compositionRatio}`}>
      {presentation === 'screen-gremlin' && <div className="screen-backdrop" data-testid="screen-backdrop">{imageUrl ? <img src={imageUrl} alt={illustrative ? 'Original illustrative screen content; not the recorded stimulus' : 'Selected source presentation frame'} style={{ objectFit: settings.backdropFit }} /> : <div className="backdrop-empty"><span>YOUR SCREEN GOES HERE</span><p>{backdropLabel}</p><small>Select a source, then explicitly Preview or Start.</small></div>}</div>}
      <div ref={host} className="flight-canvas" data-testid="flight-canvas" />
      <div className="flight-overlay"><span className="stage-mark">FLYJAM<span>ONE VERY SMALL PROBLEM</span></span><span className="stage-mode">{actualMode}</span></div>
      {!available && <div className="flight-unavailable" role="status">3D view unavailable. {graphics === 'Context creation failed' ? 'The browser could not create a WebGL2 context.' : graphics === 'Context lost' ? 'The browser lost the graphics context.' : graphics === 'Initializing' ? 'Initializing graphics.' : 'Renderer or scene initialization failed.'} Playback is disabled.</div>}
      {settings.caption && <div className="user-caption">{settings.caption}</div>}
      <div className="flight-caption">{imageLabel}</div>
    </div>
    {mode === 'synthetic' && <div className="flight-controls">
      <button onClick={() => { void load(); }} disabled={loading || playing}>Load synthetic preview</button>
      <button disabled={!preview || playing || !available || completed} onClick={() => { if (!document.hidden) { setPlaying(true); setState('Playing synthetic replay'); } }}>Play synthetic preview</button>
      <button className="secondary" disabled={!playing} onClick={() => freeze('Paused · frozen')}>Pause</button>
      <button className="secondary" disabled={!preview} onClick={() => freeze('Stopped · frozen')}>Stop</button>
      <button className="secondary" disabled={!preview} onClick={reset}>Reset preview</button>
    </div>}
    <div className="stage-summary"><span data-testid="visible-motion-state">{mode === 'synthetic' ? `Sequence: ${state}` : motionAllowed ? 'Active' : 'Stopped / paused'}</span><span>Ground: {!pose ? '—' : pose.schema_version === 'obs-flight-1' ? 'legacy · unconstrained' : pose.ground_contact ? 'contact' : 'clear'}</span></div>
    <PresentationPanel settings={settings} change={setSettings} />
    {illustrative && <details className="art-panel"><summary>Illustrative background checks</summary><label>Safe test background<select aria-label="Safe test background" value={demoBackground} onChange={e => setDemoBackground(e.target.value)}>{['white', 'black', 'colorful', 'busy'].map(name => <option key={name} value={name}>{name}</option>)}</select></label><p>Generated local art. Replay footage is unavailable.</p></details>}
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
    <details className="stage-inspector"><summary>Flight details & provenance</summary><div className="flight-telemetry" aria-label={mode === 'synthetic' ? 'Synthetic replay telemetry' : 'Flight telemetry'}>
      <p><span>PREVIEW STATE</span><strong data-testid="preview-state">{mode === 'synthetic' ? state : motionAllowed ? 'Receiving authoritative poses' : 'Frozen'}</strong></p>
      <p><span>GROUND CONTACT</span><strong data-testid="ground-contact">{!pose ? '—' : pose.schema_version === 'obs-flight-1' ? 'Legacy · unconstrained' : pose.ground_contact ? 'Contact · downward motion constrained' : 'Clear'}</strong></p>
      <p><span>SERVER TICK · 20 MS</span><strong data-testid="flight-tick">{pose?.tick ?? '—'}</strong></p>
      <p><span>POSITION · WORLD UNITS</span><strong data-testid="flight-position">{pose ? pose.position.map(value => value.toFixed(2)).join(' / ') : '—'}</strong></p>
    </div>
    {mode === 'synthetic' ? <p className="flight-explanation">A fixed synthetic control sequence, computed by the server’s flight physics. This is a visual development preview; real neural output is not connected to this stage. The browser interpolates saved poses. Wing motion is decorative. Pause and Stop freeze travel; Reset returns to the first pose. Built with locally bundled <a href={threeLicenseUrl}>three.js (MIT)</a>.</p> : <p className="flight-explanation">Server-authoritative flight poses; display interpolation ends within 100 ms of the last accepted snapshot. Connection loss, stale state and Stop freeze travel. Wing motion is decorative. Built with locally bundled <a href={threeLicenseUrl}>three.js (MIT)</a>.</p>}
    </details><output aria-hidden="true" className="pose-evidence" data-testid="rendered-pose" aria-label="Rendered pose">{JSON.stringify(rendered)}</output>
  </section>;
}
