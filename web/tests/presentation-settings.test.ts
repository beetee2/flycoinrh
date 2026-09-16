import { describe, expect, it } from 'vitest';
import { DEFAULT_PRESENTATION_SETTINGS, exportPresentationSettings, parsePresentationSettings } from '../src/live/presentationSettings';
describe('view-only Screen Gremlin settings', () => {
  it('round trips the versioned presentation whitelist', () => {
    expect(parsePresentationSettings(exportPresentationSettings({ ...DEFAULT_PRESENTATION_SETTINGS, caption: 'One very small problem.' }))).toEqual({ ...DEFAULT_PRESENTATION_SETTINGS, caption: 'One very small problem.' });
  });
  it.each(['url', 'owner_token', 'session_id', 'source_id', 'seed', 'model', 'physics', 'pixels', 'file'])('rejects extra %s keys', key => {
    expect(() => parsePresentationSettings({ ...DEFAULT_PRESENTATION_SETTINGS, [key]: 'forbidden' })).toThrow();
  });
  it.each([NaN, Infinity, -1, 1000, '16'])('rejects invalid camera distance %s', cameraDistance => {
    expect(() => parsePresentationSettings({ ...DEFAULT_PRESENTATION_SETTINGS, cameraDistance })).toThrow();
  });
  it('rejects unknown version, non-object input, oversized/control-character captions and missing fields', () => {
    for (const input of [null, [], {}, { ...DEFAULT_PRESENTATION_SETTINGS, schema_version: 'screen-gremlin-v2' }, { ...DEFAULT_PRESENTATION_SETTINGS, caption: 'a'.repeat(101) }, { ...DEFAULT_PRESENTATION_SETTINGS, caption: 'bad\ncaption' }]) expect(() => parsePresentationSettings(input)).toThrow();
  });
});
