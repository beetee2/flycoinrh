import { useEffect, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { MOTORS, parseLabResult, parseLabStatus, preset } from './lab-contracts';
import type { LabResult, LabStatus, Pixels, Population } from './lab-contracts';
import './lab.css';

const PRESETS = ['Black', 'White', 'Vertical stripes', 'Horizontal stripes', 'Checkerboard'];
const fmt = (v: number) => Number.isInteger(v) ? String(v) : v.toFixed(4);
function PixelMap({ values, label, mode = 'pixels', covered }: { values: number[]; label: string; mode?: 'pixels' | 'L1' | 'L2' | 'coverage'; covered?: number[] }) {
  const max = mode === 'L1' ? 180 : mode === 'L2' ? 108 : Math.max(1, ...values);
  return <svg viewBox="0 0 16 16" role="img" aria-label={label} className={`lab-map ${mode}`}>
    <title>{label}</title>
    {values.map((v, i) => {
      const discarded = covered && covered[i] === 0;
      const fill = discarded ? '#272936' : mode === 'pixels' ? `rgb(${v},${v},${v})` : mode === 'coverage' ? (v ? '#d6dc87' : '#272936') : mode === 'L1' ? `rgb(${Math.round(15 + 75*v/max)},${Math.round(35 + 185*v/max)},${Math.round(45 + 198*v/max)})` : `rgb(${Math.round(45 + 209*v/max)},${Math.round(25 + 139*v/max)},${Math.round(20 + 64*v/max)})`;
      return <g key={i}><rect x={i % 16} y={Math.floor(i / 16)} width="1" height="1" fill={fill}><title>{`Pixel ${i}: ${discarded ? 'unsampled' : v}`}</title></rect>{discarded && <path d={`M${i%16+.2},${Math.floor(i/16)+.2}l.6,.6`} stroke="#858391" strokeWidth=".07"/>}</g>;
    })}
  </svg>;
}
function Editor({ side, pixels, setPixels, disabled }: { side: 'A' | 'B'; pixels: Pixels; setPixels: Dispatch<SetStateAction<Pixels>>; disabled: boolean }) {
  const [brush, setBrush] = useState(255);
  const drawing = useRef(false);
  const paint = (i: number) => { if (!disabled) setPixels(current => current.map((v, j) => j === i ? brush : v)); };
  return <section className="lab-editor" aria-label={`Pattern ${side} editor`}>
    <div className="lab-card-title"><h2><span className="lab-side">{side}</span> Pattern {side}</h2><span>16 × 16 · uint8</span></div>
    <div className="lab-editor-body">
      <div className="lab-pixel-editor" role="group" aria-label={`Pattern ${side} pixels`} onPointerMove={e => {
        if (!drawing.current || e.buttons !== 1) return;
        const target = document.elementFromPoint(e.clientX, e.clientY)?.closest<HTMLButtonElement>('button[data-pixel]');
        if (target && e.currentTarget.contains(target)) paint(Number(target.dataset.pixel));
      }} onPointerCancel={() => { drawing.current = false; }} onPointerUp={() => { drawing.current = false; }} onPointerLeave={() => { drawing.current = false; }}>
        {pixels.map((value, i) => <button key={i} type="button" disabled={disabled} style={{ background: `rgb(${value},${value},${value})` }} aria-label={`${side} pixel row ${Math.floor(i/16)+1} column ${i%16+1}: ${value}`} data-pixel={i} onPointerDown={e => { if (e.button === 0) { drawing.current = true; paint(i); } }} onPointerEnter={e => { if (drawing.current && e.buttons === 1) paint(i); }} onClick={() => paint(i)} />)}
      </div>
      <div className="lab-editor-tools"><label>Preset for {side}<select aria-label={`Preset for ${side}`} defaultValue="" disabled={disabled} onChange={e => { setPixels(preset(e.target.value)); e.target.value = ''; }}><option value="" disabled>Choose a pattern</option>{PRESETS.map(p => <option key={p}>{p}</option>)}</select></label>
        <label>Brush intensity · <output>{brush}</output><input aria-label={`Brush intensity for ${side}`} type="range" min="0" max="255" step="1" value={brush} disabled={disabled} onChange={e => setBrush(Number(e.target.value))}/></label>
        <div className="lab-ramp"><span>0 black</span><span>255 white</span></div><p>Draw with a pointer, or focus a pixel and press Enter or Space. Each cell is one input pixel.</p>
        <p className="lab-brightness">Mean intensity <strong>{fmt(pixels.reduce((a,b) => a+b,0)/256)}</strong> / 255</p>
      </div>
    </div>
  </section>;
}
function driveGrid(pop: Population) {
  const sums = Array(256).fill(0);
  pop.pixel_indices.forEach((pixel, i) => { if (pixel >= 0 && pixel < 256) sums[pixel] += pop.drive_hz[i]; });
  return sums.map((v, i) => pop.coverage_counts[i] ? v / pop.coverage_counts[i] : 0);
}
function Result({ result, stale }: { result: LabResult; stale: boolean }) {
  const c = result.comparison;
  const [downloadError, setDownloadError] = useState('');
  const download = () => {
    try {
      const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)+'\n'], { type: 'application/json' }));
      const a = document.createElement('a'); a.href = url; a.download = `${result.result_id}.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch { setDownloadError('The browser could not download the result.'); }
  };
  return <section className="lab-results" aria-label="Comparison result">
    <div className="lab-result-heading"><div><p className="lab-kicker">RESULT / {result.result_id}</p><h2>Trace the response.</h2><p>{result.fixture ? 'FIXTURE — NOT REAL MODEL' : 'Real model'} · {result.cached ? 'CACHED result — no new live inference' : 'Fresh inference result'} · {result.created_at}</p></div><button onClick={download}>Download result JSON</button></div>
    {downloadError && <p role="alert">{downloadError}</p>}
    {stale && <p className="lab-notice" role="status">Editors changed after this run. All results below show the last submitted pixels. Press Run comparison to submit edits.</p>}
    <div className="lab-section-label"><span>01</span><h3>Exact submitted pixels</h3><p>Grayscale intensity · 0–255 · row-major order</p></div>
    <div className="lab-pair">{(['A','B'] as const).map(side => <div className="lab-input-card" key={side}><h4>Submitted {side}</h4><PixelMap values={result.request[side === 'A' ? 'a' : 'b']} label={`Exact submitted pattern ${side}`} /><details><summary>All 256 pixel values · {side}</summary><pre data-testid={`submitted-${side}`}>{Array.from({length:16},(_,r) => result.request[side === 'A' ? 'a' : 'b'].slice(r*16,r*16+16).map(v => String(v).padStart(3)).join(' ')).join('\n')}</pre></details></div>)}</div>
    <div className="lab-section-label"><span>02</span><h3>Retinal sampling & input drive</h3><p>Signals delivered to L1/L2 · input drive is not neuron firing</p></div>
    <p className="lab-explanation">Crossed cells are unsampled: their information is discarded at this boundary. Coverage counts are actual neuron-to-pixel assignments. Multiple neurons can sample one pixel; drive maps show their mean input rate at that pixel. Per-neuron values and identities are retained in JSON.</p>
    <div className="lab-pair">{(['A','B'] as const).map(side => { const r = result.retina[side]; return <article className="lab-retina-card" key={side}><h4>Pattern {side} · {r.sampled_pixel_count} / 256 pixels sampled</h4><p>{r.discarded_pixel_indices.length} pixels discarded · Missing coordinates: L1 {r.populations.L1.missing_coordinates}, L2 {r.populations.L2.missing_coordinates}</p><div className="lab-retina-maps"><figure><PixelMap values={r.union_coverage_counts} covered={r.union_coverage_counts} mode="coverage" label={`${side} actual L1 and L2 sampling coverage`} /><figcaption>Combined coverage<br/>lit = sampled, × = discarded</figcaption></figure>{(['L1','L2'] as const).map(pop => { const values = driveGrid(r.populations[pop]); return <figure key={pop}><PixelMap values={values} covered={r.populations[pop].coverage_counts} mode={pop} label={`${side} ${pop} input drive in Hz, not neuron firing`} /><figcaption>{pop} input drive · Hz<br/>0–{pop === 'L1' ? 180 : 108} · shared scale</figcaption></figure>; })}</div><details><summary>L1/L2 coverage counts · {side}</summary>{(['L1','L2'] as const).map(pop => <div key={pop}><h5>{pop} · neurons per pixel</h5><pre>{Array.from({length:16},(_,row) => r.populations[pop].coverage_counts.slice(row*16,row*16+16).map(v => String(v).padStart(4)).join(' ')).join('\n')}</pre></div>)}</details></article>; })}</div>
    <div className="lab-section-label"><span>03</span><h3>Measured neural response</h3><p>Output rates · Hz (spikes per second per neuron)</p></div>
    <div className="lab-controls-summary"><p><strong>{c.same_image ? 'Same-image control' : 'Different input patterns'}</strong> · {c.equal_brightness ? 'Equal mean brightness' : 'Different mean brightness'}. A: {fmt(c.mean_brightness_u8.A)}, B: {fmt(c.mean_brightness_u8.B)} / 255.</p><p><strong>Same-seed A repeatability: {c.same_seed_repeatable ? 'PASS' : 'FAIL'}</strong> · A and A repeat compared for each of {result.seeds.length} seeds. Different-seed variation is reported separately below.</p></div>
    <p className="lab-explanation">Matched seeds: {result.seeds.join(', ')} (n = {result.seeds.length}). Each run uses the same reset mode and 20 ms window. Means and sample standard deviations (SD) summarize variation across seeds; Δ is paired B − A. Matching motor rates do not establish identical whole-brain activity. Tables round to four decimal places; JSON retains full numeric precision.</p>
    <div className="lab-table-wrap"><table aria-label="Matched seed motor comparison"><thead><tr><th>Motor population</th><th>A mean ± SD (Hz)</th><th>B mean ± SD (Hz)</th><th>Paired Δ mean ± SD (Hz)</th><th>Paired Δ per seed (Hz)</th></tr></thead><tbody>{MOTORS.map(m => { const d = c.motor_rates_hz[m]; return <tr key={m}><th>{m}<br/><span className="lab-population-name">{{steer_L:'DNa02 · L',steer_R:'DNa02 · R',fwd_L:'DNa01 · L',fwd_R:'DNa01 · R',back:'MDN',stop:'DNp09',click:'MN9'}[m]}</span></th><td data-testid={`mean-A-${m}`}>{fmt(d.a_mean)} ± {fmt(d.a_sd)}</td><td>{fmt(d.b_mean)} ± {fmt(d.b_sd)}</td><td>{fmt(d.delta_mean)} ± {fmt(d.delta_sd)}</td><td>{d.paired_deltas.map(fmt).join(', ')}</td></tr>; })}</tbody></table></div>
    <details open><summary>Raw motor-population rates · all samples</summary><div className="lab-table-wrap"><table aria-label="Raw motor rates"><thead><tr><th>Input</th><th>Seed</th>{MOTORS.map(m => <th key={m}>{m} (Hz)</th>)}</tr></thead><tbody>{result.samples.map(s => <tr key={`${s.side}-${s.seed}`}><th>{s.side}</th><td>{s.seed}</td>{MOTORS.map(m => <td data-testid={`rate-${s.side}-${s.seed}-${m}`} key={m}>{fmt(s.motor_rates_hz[m])}</td>)}</tr>)}</tbody></table></div></details>
    <details><summary>Existing neural statistics · all samples</summary><p className="lab-explanation">Neuron count covers the graph. Spike total covers the entire 20 ms window; spikes/s is the whole-graph total divided by 0.02 s. Firing, visual, and motor counters count distinct neurons firing at least once during the 20 ms window. Mean membrane voltage is measured on the final step.</p><div className="lab-table-wrap"><table aria-label="Raw neural statistics"><thead><tr><th>Input / seed</th><th>Neurons</th><th>Total spikes</th><th>Spikes/s</th><th>Mean mV</th><th>Active neurons (20 ms)</th><th>Active visual (20 ms)</th><th>Active motor (20 ms)</th></tr></thead><tbody>{result.samples.map(s => <tr key={`${s.side}-${s.seed}`}><th>{s.side} / {s.seed}</th>{['sampled_neurons','spike_count','spikes_per_sec','mean_mv','firing','visual','motor'].map(k => <td data-testid={`stat-${s.side}-${s.seed}-${k}`} key={k}>{fmt(s.statistics[k])}</td>)}</tr>)}</tbody></table></div></details>
    <details><summary>Model, data, source, runtime & input identities</summary><pre>{JSON.stringify(result.identities,null,2)}</pre></details>
  </section>;
}
export function Lab() {
  const [a,setA] = useState(() => preset('Vertical stripes'));
  const [b,setB] = useState(() => preset('Horizontal stripes'));
  const [status,setStatus] = useState<LabStatus|null>(null);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [result,setResult] = useState<LabResult|null>(null);
  async function checkStatus() {
    try { const r = await fetch('/api/lab/status'); if (!r.ok) throw new Error('Local model service is unavailable.'); setStatus(parseLabStatus(await r.json())); setError(''); }
    catch (e) { setStatus(null); setError(e instanceof Error ? e.message : 'Unable to check the local service.'); }
  }
  useEffect(() => { void checkStatus(); }, []);
  async function run() {
    if (busy || status?.state !== 'ready') return;
    setBusy(true); setError('');
    try {
      const r = await fetch('/api/lab/compare', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({schema_version:'flytrap-lab-request-1',a,b}) });
      const value = await r.json();
      if (!r.ok) throw new Error(typeof value.detail === 'string' ? value.detail : `Comparison failed (HTTP ${r.status}).`);
      const next = parseLabResult(value);
      if (JSON.stringify(next.request.a) !== JSON.stringify(a) || JSON.stringify(next.request.b) !== JSON.stringify(b)) throw new Error('The result pixels do not match the submitted inputs.');
      setResult(next);
      setStatus(s => s && ({...s,attempted_calls:next.attempted_calls}));
    } catch(e) { setError(e instanceof Error ? e.message : 'Comparison failed.'); }
    finally {
      // Count failed model attempts too; a status read never launches inference.
      try {
        const refresh = await fetch('/api/lab/status');
        if (refresh.ok) setStatus(parseLabStatus(await refresh.json()));
      } catch { /* Preserve the comparison error or result if status refresh fails. */ }
      setBusy(false);
    }
  }
  const stale = !!result && (JSON.stringify(a) !== JSON.stringify(result.request.a) || JSON.stringify(b) !== JSON.stringify(result.request.b));
  const budgetAvailable = !!status && status.attempted_calls + status.calls_per_comparison <= status.call_cap;
  return <main className="lab-shell">
    <header className="lab-header"><a href="/lab" aria-label="FLYTRAP LAB home">FLYTRAP<span>LAB</span></a><span className="lab-badge">P00 · LOCAL PROTOTYPE</span></header>
    <section className="lab-intro"><p className="lab-kicker">STIMULUS → RETINA → RESPONSE</p><h1>Two patterns.<br/><span>Follow the signal.</span></h1><p>Draw grayscale inputs. Inspect what this simulation actually samples, then compare the measured neural responses.</p><div className="lab-baseline">Untrained baseline <span>·</span> windowed_reset <span>·</span> 20 ms per sample</div></section>
    <div className="lab-pair"><Editor side="A" pixels={a} setPixels={setA} disabled={busy}/><Editor side="B" pixels={b} setPixels={setB} disabled={busy}/></div>
    <div className="lab-action-bar"><button className="lab-secondary" disabled={busy} onClick={() => setB([...a])}>Copy A to B · same-image control</button><div className="lab-run-area"><p>Seeds 17, 29, 43 · 9 model calls per comparison<br/>{status ? `${status.attempted_calls} / ${status.call_cap} attempted calls used` : 'Checking local call budget…'}</p><button className="lab-run" disabled={busy || status?.state !== 'ready' || !budgetAvailable} onClick={() => void run()}>{busy ? 'Running comparison…' : 'Run comparison'}<span aria-hidden="true"> ↗</span></button></div></div>
    <div className="lab-service" role="status" aria-label="Local model status">{busy ? 'Busy · one isolated model job is running. This can take several seconds.' : status ? `${status.state === 'ready' ? 'Ready' : status.state === 'busy' ? 'Busy' : 'Unavailable'} · ${status.message}${!budgetAvailable ? ' Call budget cannot admit another comparison.' : ''}` : 'Local model status unavailable or loading.'}</div>
    {!busy && <button className="lab-refresh" onClick={() => void checkStatus()}>Refresh service status</button>}
    {error && <p className="lab-error" role="alert">{error}</p>}
    {result ? <Result result={result} stale={stale}/> : <div className="lab-empty"><span>01 / PIXELS</span><span>02 / RETINAL INPUT</span><span>03 / NEURAL OUTPUT</span><p>Press Run comparison to trace both patterns through the real local model. Initial stripes have equal mean brightness.</p></div>}
    <footer className="lab-footer"><strong>Non-production · local use only</strong><p>This is a stimulus-response explorer. These measurements do not demonstrate perception, preference, recognition, learning, biological vision, or intelligence. P00 engineering validation does not imply product approval.</p></footer>
  </main>;
}
