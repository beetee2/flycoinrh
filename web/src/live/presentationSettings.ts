/** View-only settings. No source identity, capture controls, or authoritative state. */
export type PresentationSettings = {
  schema_version: 'screen-gremlin-v1';
  cameraDistance: number;
  cameraFov: number;
  followDeadZone: number;
  keyLightIntensity: number;
  wingOpacity: number;
  backdropFit: 'contain' | 'cover';
  caption: string;
  compositionRatio: 'landscape' | 'portrait';
};
export const DEFAULT_PRESENTATION_SETTINGS: Readonly<PresentationSettings> = Object.freeze({
  schema_version: 'screen-gremlin-v1', cameraDistance: 12, cameraFov: 42, followDeadZone: 1.7,
  keyLightIntensity: 3.2, wingOpacity: .48, backdropFit: 'contain', caption: '', compositionRatio: 'landscape',
});
export function parsePresentationSettings(input: unknown): PresentationSettings {
  const value: unknown = typeof input === 'string' ? JSON.parse(input) : input;
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Expected presentation settings.');
  const record = value as Record<string, unknown>;
  if (Object.keys(record).length !== Object.keys(DEFAULT_PRESENTATION_SETTINGS).length ||
      Object.keys(record).some(key => !(key in DEFAULT_PRESENTATION_SETTINGS)) || record.schema_version !== 'screen-gremlin-v1') {
    throw new Error('Unknown presentation setting or version.');
  }
  const bounds = { cameraDistance: [12, 24], cameraFov: [32, 55], followDeadZone: [0, 4], keyLightIntensity: [.5, 6], wingOpacity: [.15, .8] } as const;
  for (const [key, [low, high]] of Object.entries(bounds)) {
    const entry = record[key];
    if (typeof entry !== 'number' || !Number.isFinite(entry) || entry < low || entry > high) throw new Error(`Invalid ${key}.`);
  }
  if (record.backdropFit !== 'contain' && record.backdropFit !== 'cover') throw new Error('Invalid backdrop fit.');
  if (record.compositionRatio !== 'landscape' && record.compositionRatio !== 'portrait') throw new Error('Invalid composition ratio.');
  if (typeof record.caption !== 'string' || [...record.caption].length > 100 || /[\u0000-\u001f\u007f]/u.test(record.caption)) throw new Error('Caption must contain at most 100 printable characters.');
  return { ...record } as PresentationSettings;
}
export function exportPresentationSettings(settings: PresentationSettings): string {
  return JSON.stringify(parsePresentationSettings(settings), null, 2);
}
