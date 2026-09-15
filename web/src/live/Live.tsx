import { lazy, Suspense, useEffect, useRef, useState } from 'react';
const FlightStage = lazy(() => import('./FlightStage').then(module => ({ default: module.FlightStage })));
import { parseLiveContract } from './contracts';
import type { ApiSnapshot, FlightSnapshot, LiveConfig, ReplayList, ReplayPayload, SourceCapability, SourcePreview } from './contracts';
import { SessionClient } from './session-client';
import type { StageMode } from './FlightStage';

const activeStates = new Set(['previewing', 'starting', 'running', 'stopping']);
function message(cause: unknown) { return cause instanceof Error ? cause.message : 'Local service is unavailable.'; }
function Pixels({ bytes, label }: { bytes: number[]; label: string }) {
  return <svg role="img" aria-label={label} viewBox="0 0 16 16" className="input-pixels" shapeRendering="crispEdges">
    {bytes.map((value, index) => <rect key={index} x={index % 16} y={Math.floor(index / 16)} width="1" height="1" fill={`rgb(${value},${value},${value})`} />)}
  </svg>;
}


/** Ephemeral, validated low-resolution source thumbnail; never persisted. */
export function SourceThumbnail({ source }: { source: SourcePreview }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => {
    const target = canvas.current;
    if (!target) return;
    let context: CanvasRenderingContext2D | null = null;
    try {
      context = target.getContext('2d');
      if (!context) throw new Error('Source thumbnail canvas unavailable.');
      const rgb = atob(source.rgb_base64);
      const pixels = context.createImageData(source.width, source.height);
      for (let pixel = 0; pixel < source.width * source.height; pixel++) {
        pixels.data[pixel * 4] = rgb.charCodeAt(pixel * 3);
        pixels.data[pixel * 4 + 1] = rgb.charCodeAt(pixel * 3 + 1);
        pixels.data[pixel * 4 + 2] = rgb.charCodeAt(pixel * 3 + 2);
        pixels.data[pixel * 4 + 3] = 255;
      }
      context.putImageData(pixels, 0, 0); setUnavailable(false);
    } catch { setUnavailable(true); }
    return () => { context?.clearRect(0, 0, source.width, source.height); };
  }, [source]);
  return <><canvas ref={canvas} width={source.width} height={source.height} role="img"
    aria-label="Newest source RGB thumbnail" data-testid="source-preview-canvas" className="source-thumbnail" />
    {unavailable && <p>Source thumbnail unavailable in this browser.</p>}</>;
}

export function Live() {
  const [config, setConfig] = useState<LiveConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sources, setSources] = useState<SourceCapability[]>([]);
  const [sourceId, setSourceId] = useState('');
  const [mode, setMode] = useState<StageMode>('synthetic');
  const [snapshot, setSnapshot] = useState<ApiSnapshot | null>(null);
  const [freezePose, setFreezePose] = useState(false);
  const [neutral, setNeutral] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [graphicsReady, setGraphicsReady] = useState(false);
  const [renderHz, setRenderHz] = useState(0);
  const [duration, setDuration] = useState(120);
  const [calls, setCalls] = useState(512);
  const [seed, setSeed] = useState(0);
  const [record, setRecord] = useState(false);
  const [inspect, setInspect] = useState(false);
  const [latest, setLatest] = useState<SourcePreview | null>(null);
  const [recordings, setRecordings] = useState<ReplayList['recordings']>([]);
  const [recordingId, setRecordingId] = useState('');
  const [replay, setReplay] = useState<ReplayPayload | null>(null);
  const [loadedRecordingId, setLoadedRecordingId] = useState('');
  const [replayPose, setReplayPose] = useState<FlightSnapshot | null>(null);
  const [replayTick, setReplayTick] = useState(0);
  const [replayPlaying, setReplayPlaying] = useState(false);
  const [receivedAt, setReceivedAt] = useState(0);
  const [clock, setClock] = useState(0);
  const client = useRef<SessionClient | null>(null);
  const mounted = useRef(false);
  const action = useRef(0);
  const selected = sources.find(source => source.source_id === sourceId);
  const active = snapshot !== null && activeStates.has(snapshot.status.state) && !neutral;
  const recordingAllowed = selected?.backend === 'synthetic';
  const stale = active && mode === 'live' && clock - receivedAt > 2000;
  const motionAllowed = mode === 'replay' ? replayPlaying : active && !stale && snapshot?.status.state === 'running';

  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    const connection = new SessionClient({
      onSnapshot: value => {
        if (!mounted.current) return;
        setSnapshot(value); setReceivedAt(performance.now()); setClock(performance.now());
        if (!activeStates.has(value.status.state)) setNeutral(value.status.reason ?? value.status.state);
      },
      onNeutral: reason => {
        if (!mounted.current) return;
        setNeutral(reason); setRenderHz(0);
        if (reason !== 'Session is terminal.') setFreezePose(true);
      },
    });
    client.current = connection;
    async function read(path: string) {
      const response = await fetch(path, { method: 'GET', signal: controller.signal, cache: 'no-store' });
      if (!response.ok) throw new Error(`Local service returned HTTP ${response.status}.`);
      return response.json() as Promise<unknown>;
    }
    void Promise.all([read('/health/live'), read('/api/live/config'), connection.sources(), connection.status()]).then(([health, settings, list, status]) => {
      parseLiveContract('LiveHealth', health);
      const checked = parseLiveContract('LiveConfig', settings);
      if (controller.signal.aborted) return;
      setConfig(checked); setSources(list.sources);
      if (status.current) { setSnapshot(status.current); setNeutral(`Existing session · ${status.current.status.state}${status.current.status.reason ? ` · ${status.current.status.reason}` : ''} · this tab does not own capture.`); }
    }).catch(cause => { if (!controller.signal.aborted) setError(message(cause)); });
    const timer = setInterval(() => setClock(performance.now()), 250);
    const hide = () => { if (document.hidden) { setReplayPlaying(false); setBusy(false); action.current++; } };
    document.addEventListener('visibilitychange', hide);
    return () => {
      mounted.current = false; action.current++; controller.abort(); clearInterval(timer);
      document.removeEventListener('visibilitychange', hide); connection.dispose(); client.current = null;
    };
  }, []);

  useEffect(() => {
    if (stale) { client.current?.stop(); setNeutral('Stale session state · explicit Start required.'); }
  }, [stale]);

  useEffect(() => {
    if (!inspect || !active || !snapshot) return;
    const target = snapshot.status;
    let valid = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const reply = await client.current!.previewFrame(target.session_id, target.generation);
        if (valid) setLatest(previous => !previous || !reply.latest || reply.latest.frame.sequence >= previous.frame.sequence ? reply.latest : previous);
      } catch (cause) {
        if (valid) { client.current?.stop(); setError(message(cause)); }
      }
      if (valid) timer = setTimeout(() => { void poll(); }, 250);
    };
    void poll();
    return () => { valid = false; clearTimeout(timer); };
  }, [inspect, active, snapshot?.status.session_id, snapshot?.status.generation]);

  // Terminal recording publication may finish after resources have been reaped.
  useEffect(() => {
    if (!snapshot || active || !neutral) return;
    let valid = true;
    let count = 0;
    const timer = setInterval(() => {
      if (count++ >= 12) { clearInterval(timer); return; }
      void client.current?.status().then(value => {
        if (valid && value.current?.status.session_id === snapshot.status.session_id && value.current.status.generation === snapshot.status.generation) setSnapshot(previous => !previous || value.current!.event_sequence >= previous.event_sequence ? value.current : previous);
      }).catch(() => {});
      void client.current?.config().then(value => { if (valid) setConfig(value); }).catch(() => {});
    }, 500);
    return () => { valid = false; clearInterval(timer); };
  }, [snapshot?.status.session_id, active, neutral]);

  function switchMode(next: StageMode) {
    action.current++; client.current?.stop(); setBusy(false); setReplayPlaying(false); setMode(next);
    setError(null); setLatest(null); setRecord(false); setNeutral(null); setSnapshot(null); setFreezePose(false);
  }
  function stop() {
    action.current++; client.current?.stop(); setReplayPlaying(false); setBusy(false); setRenderHz(0);
  }
  async function start(preview: boolean) {
    if (!selected || !client.current || busy) return;
    if (!Number.isInteger(duration) || duration < 1 || duration > 120 || !Number.isInteger(calls) || calls < 1 || calls > 512 || !Number.isInteger(seed) || seed < 0 || seed > 4294967295) {
      setError('Use a duration from 1 to 120 seconds, 1 to 512 model calls, and an integer seed from 0 to 4294967295.'); return;
    }
    const serial = ++action.current;
    setBusy(true); setError(null); setNeutral(null); setLatest(null); setSnapshot(null); setFreezePose(false);
    setMode(preview ? 'preview' : 'live'); setReplayPlaying(false);
    try {
      await client.current.inspect(selected.source_id);
      if (serial !== action.current || document.hidden) return;
      const acquired = preview ? await client.current.preview(selected.source_id, Math.min(duration, 30)) : await client.current.start({
        source_id: selected.source_id, evidence_kind: selected.evidence_kind, seed,
        duration_seconds: duration, max_model_calls: calls, recording: record && recordingAllowed,
      }, record && recordingAllowed);
      if (serial !== action.current) { client.current?.stop(); return; }
      if (activeStates.has(acquired.status.state)) await client.current.connect(acquired.status.session_id, acquired.status.generation);
    } catch (cause) { if (serial === action.current) { client.current?.stop(); setError(message(cause)); } }
    finally { if (serial === action.current) { setBusy(false); setRecord(false); } }
  }
  async function refreshRecordings() {
    try { const list = await client.current!.replays(); if (mounted.current) setRecordings(list.recordings); }
    catch (cause) { setError(message(cause)); }
  }
  async function loadRecording() {
    stop(); const loadSerial = action.current;
    setBusy(true); setError(null); setReplay(null); setReplayPose(null);
    try {
      const loaded = await client.current!.replay(recordingId);
      if (!mounted.current || loadSerial !== action.current) return;
      setReplay(loaded); setLoadedRecordingId(recordingId); setReplayTick(0); setReplayPose(loaded.manifest.initial_flight); setMode('replay');
    } catch (cause) { if (loadSerial === action.current) setError(message(cause)); }
    finally { if (loadSerial === action.current) setBusy(false); }
  }
  async function seek(tick: number) {
    if (!replay) return;
    const serial = ++action.current;
    setReplayPlaying(false);
    try {
      const state = await client.current!.seek(loadedRecordingId, tick);
      if (serial !== action.current) return;
      if (state.snapshot.session_id !== replay.manifest.session_id || state.snapshot.generation !== replay.manifest.generation || state.snapshot.tick !== tick) throw new Error('Foreign replay seek state.');
      setReplayTick(tick); setReplayPose(state.snapshot);
    } catch (cause) { if (serial === action.current) setError(message(cause)); }
  }
  useEffect(() => {
    if (!replayPlaying || !replay) return;
    let valid = true;
    let timer: ReturnType<typeof setTimeout>;
    const origin = performance.now() - replayTick * 20;
    const update = async () => {
      const tick = Math.min(replay.trace.ticks, Math.floor((performance.now() - origin) / 20));
      try {
        const state = await client.current!.seek(loadedRecordingId, tick);
        if (!valid) return;
        if (state.snapshot.session_id !== replay.manifest.session_id || state.snapshot.generation !== replay.manifest.generation || state.snapshot.tick !== tick) throw new Error('Foreign replay seek state.');
        setReplayTick(tick); setReplayPose(state.snapshot);
        if (tick >= replay.trace.ticks) setReplayPlaying(false);
        else timer = setTimeout(() => { void update(); }, 100);
      } catch (cause) { if (valid) { setError(message(cause)); setReplayPlaying(false); } }
    };
    void update();
    return () => { valid = false; clearTimeout(timer); };
    // A single paced reader owns playback until Pause/seek/mode change.
  }, [replayPlaying, replay, loadedRecordingId]);

  async function download() {
    if (!replay || !client.current) return;
    const serial = action.current;
    const id = loadedRecordingId;
    try {
      const blob = await client.current.download(id);
      if (!mounted.current || serial !== action.current) return;
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a'); link.href = url; link.download = `${id}.json`; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (cause) { if (mounted.current && serial === action.current) setError(message(cause)); }
  }
  const replayResponse = replay && replayPose ? [...replay.trace.events].reverse().find(event => event.tick <= replayPose.tick && event.controls)?.controls?.response_id : null;
  const inferred = mode === 'replay' ? replay?.samples.find(sample => sample.response_id === replayResponse) ?? null : snapshot?.last_inferred;
  const pose = mode === 'replay' ? replayPose : snapshot?.flight ?? null;
  const age = (value: number | null | undefined) => value == null ? 'Unknown' : `${Math.round(value + (active ? Math.max(0, clock - receivedAt) : 0))} ms`;
  const status = mode === 'replay' ? replay ? `${replayPlaying ? 'Playing' : 'Paused'} · recorded playback` : 'Choose a recording' : neutral ?? snapshot?.status.state ?? (config ? 'Idle · local service available' : 'Checking local service…');
  return <div className="shell">
    <header className="masthead"><a className="wordmark" href="/live">FLYJAM <span>LIVE</span></a><span className="edition">LOCAL · OBS05</span></header>
    <main>
      <section className="intro"><p className="eyebrow">OBS TO FLIGHT</p><h1>A fly, in open air.</h1>
        <p className="lede">Choose a source, inspect its input, then start a bounded neural flight session.</p></section>
      <nav className="mode-controls" aria-label="Flight experience">
        <button aria-pressed={mode === 'synthetic'} onClick={() => switchMode('synthetic')}>Synthetic demonstration</button>
        <button aria-pressed={mode === 'live' || mode === 'preview'} onClick={() => switchMode('live')}>Live source</button>
        <button aria-pressed={mode === 'replay'} onClick={() => { switchMode('replay'); void refreshRecordings(); }}>Recorded playback</button>
      </nav>
      <Suspense fallback={<p>Loading flight stage…</p>}><FlightStage mode={mode} modelMode={snapshot?.model_mode ?? 'none'} snapshot={pose} motionAllowed={motionAllowed} freezePose={freezePose}
        onGraphicsReady={setGraphicsReady} onRenderingRate={setRenderHz} onGraphicsFailure={() => { stop(); setNeutral('Graphics unavailable · retry graphics, then explicitly Start.'); }} /></Suspense>
      <section className="status-card" aria-labelledby="live-status-title">
        <h2 id="live-status-title">Session controls</h2>
        <p role="status" data-testid="session-status" className="availability">{status}</p>
        {error && <div role="alert" className="error">{error}</div>}
        {(mode === 'live' || mode === 'preview') && <>
          <div className="session-fields">
            <label>Source<select value={sourceId} disabled={active || busy} onChange={event => { setSourceId(event.target.value); setRecord(false); setLatest(null); setSnapshot(null); setNeutral(null); }}><option value="">Explicit selection required</option>
              {sources.map(source => <option key={source.source_id} value={source.source_id}>{source.name} · {source.source_id}</option>)}</select></label>
            <label>Session duration (seconds)<input type="number" min="1" max="120" value={duration} disabled={active || busy} onChange={event => setDuration(Number(event.target.value))} /></label>
            <label>Maximum model calls<input type="number" min="1" max="512" value={calls} disabled={active || busy} onChange={event => setCalls(Number(event.target.value))} /></label>
            <label>Seed<input type="number" min="0" max="4294967295" value={seed} disabled={active || busy} onChange={event => setSeed(Number(event.target.value))} /></label>
          </div>
          {selected && <p className="context">{selected.name} · {selected.backend} · producer detection: {selected.producer_detection}. Preview lasts at most 30 seconds. Keep the Flyjam output outside the selected OBS input scene.</p>}
          <label className="consent"><input type="checkbox" checked={record} disabled={!recordingAllowed || active || busy} onChange={event => setRecord(event.target.checked)} />Record this session locally</label>
          {!recordingAllowed && <p className="context">Recording is disabled for the selected monitor source.</p>}
          <div className="operator-buttons">
            <button disabled={!selected || active || busy || !config} onClick={() => { void start(true); }}>Preview source</button>
            <button disabled={!selected || active || busy || !config || !graphicsReady} onClick={() => { void start(false); }}>Start live flight</button>
            <button disabled={!active && !busy} onClick={stop}>Stop session</button>
          </div>
        </>}
        {mode === 'replay' && <div className="replay-controls">
          <button onClick={() => { void refreshRecordings(); }}>Refresh recordings</button>
          <label>Recording<select value={recordingId} onChange={event => setRecordingId(event.target.value)}><option value="">Choose a local recording</option>{recordings.map(item => <option key={item.recording_id} value={item.recording_id} disabled={item.manifest?.state !== 'complete'}>{item.recording_id} · {item.manifest?.state ?? item.state ?? item.error}</option>)}</select></label>
          <button disabled={!recordingId || busy} onClick={() => { void loadRecording(); }}>Load recording</button>
          <button disabled={!replay || replayPlaying || !graphicsReady || replayTick >= (replay?.trace.ticks ?? 0)} onClick={() => { if (!document.hidden) { action.current++; setReplayPlaying(true); } }}>Play recording</button>
          <button disabled={!replayPlaying} onClick={() => setReplayPlaying(false)}>Pause recording</button>
          <label>Replay tick<input type="range" min="0" max={replay?.trace.ticks ?? 0} value={replayTick} disabled={!replay} onChange={event => { void seek(Number(event.target.value)); }} /><output>{replayTick} / {replay?.trace.ticks ?? 0}</output></label>
          <button disabled={!replay} onClick={download}>Download recording</button>
          {replay && <p>Loaded recording: <strong data-testid="loaded-recording-id">{loadedRecordingId}</strong> · session {replay.manifest.session_id}. Playback performs no capture or inference.</p>}
        </div>}
        <dl className="facts">
          <div><dt>Capture rate</dt><dd data-testid="capture-hz">{active ? (snapshot?.capture_hz ?? 0).toFixed(1) : '0.0'} Hz</dd></div>
          <div><dt>Neural update rate</dt><dd data-testid="neural-hz">{active ? (snapshot?.model_hz ?? 0).toFixed(2) : '0.00'} Hz</dd></div>
          <div><dt>Rendering rate</dt><dd data-testid="rendering-hz">{renderHz.toFixed(1)} Hz</dd></div>
          <div><dt>Model mode</dt><dd data-testid="model-mode">{mode === 'synthetic' ? 'Synthetic demonstration' : mode === 'replay' ? 'Recorded playback' : snapshot?.model_mode === 'real' ? 'Actual neural model · windowed_reset' : snapshot?.model_mode === 'fixture' ? 'Fixture model · synthetic test responses' : 'No inference'}</dd></div>
          <div><dt>Producer health</dt><dd>{snapshot?.status.producer_health ?? 'Unknown'}</dd></div>
          <div><dt>Content unchanged</dt><dd>{Math.round(snapshot?.status.content_unchanged_ms ?? 0)} ms</dd></div>
          <div><dt>Source receipt age</dt><dd>{age(snapshot?.source_receipt_age_ms)}</dd></div>
          <div><dt>Response age</dt><dd>{age(snapshot?.response_age_ms)}</dd></div>
          <div><dt>Execution purpose</dt><dd>{config?.execution_purpose ?? 'Unknown'}</dd></div>
          <div><dt>Automated allowance remaining</dt><dd>{config?.validation_remaining ?? 'Unavailable'}</dd></div>
          <div><dt>Neural calls</dt><dd data-testid="attempted-calls">{snapshot?.status.attempted_calls ?? 0}</dd></div>
          <div><dt>Recording</dt><dd data-testid="recording-state">{snapshot?.recording_state ?? 'Off by default'}</dd></div>
        </dl>
        <label className="inspection-toggle"><input type="checkbox" checked={inspect} onChange={event => setInspect(event.target.checked)} />Inspect input</label>
        {inspect && <section className="input-inspection" aria-label="Input inspection">
          <div><h3>Newest source preview</h3><p data-testid="source-preview-id">{latest ? `${latest.frame.source_id} / ${latest.frame.session_id} / ${latest.frame.generation} / ${latest.frame.sequence}` : 'No source preview'}</p>
            {latest && <><SourceThumbnail source={latest} /><p>Processed newest frame · 16×16</p><Pixels bytes={latest.observation_u8} label="Newest processed source frame" /></>}<output data-testid="source-preview-bytes" className="bytes-evidence">{JSON.stringify(latest?.observation_u8 ?? null)}</output></div>
          <div><h3>Exact last-inferred input · 16×16</h3><p data-testid="inferred-input-id">{inferred ? `${inferred.frame.source_id} / ${inferred.frame.session_id} / ${inferred.frame.generation} / ${inferred.frame.sequence} · ${inferred.response_id}` : 'Waiting for a neural response'}</p>
            {inferred && <Pixels bytes={inferred.observation_u8} label="Exact input used for displayed neural response" />}<output data-testid="inferred-input-bytes" className="bytes-evidence">{JSON.stringify(inferred?.observation_u8 ?? null)}</output></div>
          <div className="neural-inspection"><h3>Measured motor rates · Hz</h3><pre data-testid="neural-values">{JSON.stringify(inferred?.motor_rates_hz ?? null, null, 2)}</pre><p>Applied response: <span data-testid="applied-response-id">{pose?.applied_response_id ?? 'None · neutral'}</span></p>
            <p>Session: {pose?.session_id ?? 'None'} · generation {pose?.generation ?? '—'} · authoritative tick {pose?.tick ?? '—'}</p><output data-testid="authoritative-pose">{JSON.stringify(pose)}</output></div>
        </section>}
        <p className="context">Recording is off by default and requires consent on each Start. It saves private processed 16×16 inputs, raw neural responses and flight replay locally. These inputs can contain sensitive content. Downloads contain the same private processed inputs; keep them local. Full-resolution source video is never saved.</p>
        <p className="context">Hiding or closing this tab, losing the connection, source loss or graphics failure stops ownership. Recovery requires an explicit Start. A failed session stays stopped.</p>
      </section>
    </main>
    <footer><span>Private local workspace</span><span>OBS05 · <a href="http://127.0.0.1:8766/lab">Diagnostic lab</a></span></footer>
  </div>;
}
