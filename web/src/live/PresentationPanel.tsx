import { useRef, useState } from 'react';
import { DEFAULT_PRESENTATION_SETTINGS, exportPresentationSettings, parsePresentationSettings, type PresentationSettings } from './presentationSettings';

export function PresentationPanel({ settings, change }: { settings: PresentationSettings; change: (settings: PresentationSettings) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [error, setError] = useState('');
  function update<K extends keyof PresentationSettings>(key: K, value: PresentationSettings[K]) { change({ ...settings, [key]: value }); }
  async function importFile(file?: File) {
    if (!file) return;
    try {
      if (file.size > 4096) throw new Error('Settings file is too large.');
      change(parsePresentationSettings(JSON.parse(await file.text()))); setError('');
    } catch { setError('Use a valid screen-gremlin-v1 presentation settings file.'); }
    if (input.current) input.current.value = '';
  }
  function save() {
    const url = URL.createObjectURL(new Blob([exportPresentationSettings(settings)], { type: 'application/json' }));
    const link = document.createElement('a'); link.href = url; link.download = 'screen-gremlin-v1.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }
  return <details className="art-panel"><summary>Art & composition</summary>
    <div className="art-fields">
      <label>Camera distance<input type="range" min="12" max="24" step="0.1" value={settings.cameraDistance} onChange={e => update('cameraDistance', Number(e.target.value))} /><output>{settings.cameraDistance.toFixed(1)}</output></label>
      <label>Camera FOV<input type="range" min="32" max="55" step="1" value={settings.cameraFov} onChange={e => update('cameraFov', Number(e.target.value))} /><output>{settings.cameraFov}°</output></label>
      <label>Follow dead zone<input type="range" min="0" max="4" step="0.1" value={settings.followDeadZone} onChange={e => update('followDeadZone', Number(e.target.value))} /><output>{settings.followDeadZone.toFixed(1)}</output></label>
      <label>Key light<input type="range" min="0.5" max="6" step="0.1" value={settings.keyLightIntensity} onChange={e => update('keyLightIntensity', Number(e.target.value))} /></label>
      <label>Wing opacity<input type="range" min="0.15" max="0.8" step="0.01" value={settings.wingOpacity} onChange={e => update('wingOpacity', Number(e.target.value))} /></label>
      <label>Backdrop fit<select value={settings.backdropFit} onChange={e => update('backdropFit', e.target.value as 'contain' | 'cover')}><option value="contain">Contain · full image</option><option value="cover">Cover · crop edges</option></select></label>
      <label>Composition ratio<select value={settings.compositionRatio} onChange={e => update('compositionRatio', e.target.value as 'landscape' | 'portrait')}><option value="landscape">Landscape · 16:9</option><option value="portrait">Portrait · 9:16</option></select></label>
      <label className="caption-field">Caption<input maxLength={100} value={settings.caption} placeholder="A small thought, up to 100 characters" onChange={e => update('caption', e.target.value)} /><output>{settings.caption.length}/100</output></label>
    </div>
    <div className="art-actions"><button onClick={() => change({ ...DEFAULT_PRESENTATION_SETTINGS })}>Reset art settings</button><button onClick={save}>Export settings</button><button onClick={() => input.current?.click()}>Import settings</button><input ref={input} hidden type="file" accept="application/json,.json" onChange={e => void importFile(e.target.files?.[0])} /></div>
    <p>Local framing only. Composition previews do not record or export video.</p>{error && <p role="alert">{error}</p>}
  </details>;
}
