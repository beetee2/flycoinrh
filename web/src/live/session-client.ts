import { parseLiveContract, type ApiSnapshot, type ContractName, type LiveContracts, type SessionConfig, type ReplayManifest } from './contracts';

type Identity = { sessionId: string; generation: number };
type Stream = Pick<EventTarget, 'addEventListener'> & { close(): void };
type Options = {
  fetch?: typeof fetch;
  eventSource?: (url: string) => Stream;
  now?: () => number;
  document?: Pick<Document, 'hidden' | 'addEventListener' | 'removeEventListener'>;
  window?: Pick<Window, 'addEventListener' | 'removeEventListener'>;
  onSnapshot: (snapshot: ApiSnapshot) => void;
  onNeutral: (reason: string) => void;
};
type Owner = Identity & { deadline: number };
const terminal = new Set(['idle', 'stopping', 'stopped', 'source_lost', 'failed', 'limit_reached']);
const maxJsonLength = 262_144;
const same = (a: Identity, b: Identity) => a.sessionId === b.sessionId && a.generation === b.generation;
function token(): string {
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, '0')).join('');
}
function identity(sessionId: string, generation: number): Identity {
  if (!/^[a-z0-9][a-z0-9_-]{0,63}$/.test(sessionId) || !Number.isSafeInteger(generation) || generation < 1) {
    throw new Error('Invalid session identity.');
  }
  return { sessionId, generation };
}
function decode<K extends ContractName>(name: K, text: string): LiveContracts[K] {
  if (text.length > (name === 'ReplayPayload' || name === 'ReplayList' ? 33554432 : maxJsonLength)) throw new Error('Live response exceeds the client bound.');
  return parseLiveContract(name, JSON.parse(text));
}

/** Local transport only. Construction and spectator reads never acquire ownership. */
export class SessionClient {
  private readonly transport: typeof fetch;
  private readonly makeStream: (url: string) => Stream;
  private readonly now: () => number;
  private readonly doc: Options['document'] & {};
  private readonly win: Options['window'] & {};
  private readonly ownerToken = token();
  private csrf: string | null = null;
  private owner: Owner | null = null;
  private watched: Identity | null = null;
  private watchedSource: string | null = null;
  private flightTick = -1;
  private sequence = -1;
  private stream: Stream | null = null;
  private renewal: ReturnType<typeof setTimeout> | null = null;
  private expiry: ReturnType<typeof setTimeout> | null = null;
  private pendingStart = false;
  private cancelledStart = false;
  private disposed = false;
  private connection = 0;
  private readonly recordings = new Map<string, ReplayManifest>();

  constructor(private readonly options: Options) {
    this.transport = options.fetch ?? globalThis.fetch.bind(globalThis);
    this.makeStream = options.eventSource ?? (url => new EventSource(url));
    this.now = options.now ?? (() => performance.now());
    this.doc = options.document ?? document;
    this.win = options.window ?? window;
    this.doc.addEventListener('visibilitychange', this.visibility);
    this.win.addEventListener('pagehide', this.pagehide);
  }

  private visibility = () => { if (this.doc.hidden) this.release('Control tab hidden.'); };
  private pagehide = () => { this.release('Control tab closed.'); };

  private async read<K extends ContractName>(path: string, name: K, init?: RequestInit): Promise<LiveContracts[K]> {
    const response = await this.transport(`/api/live${path}`, { credentials: 'same-origin', ...init });
    if (!response.ok) throw new Error(`Local session request failed (${response.status}).`);
    return decode(name, await response.text());
  }

  async control() {
    const result = await this.read('/control', 'ControlBootstrap');
    this.csrf = result.csrf_token;
    return result;
  }
  sources() { return this.read('/sources', 'SourceList'); }
  config() { return this.read('/config', 'LiveConfig'); }
  status() { return this.read('/status', 'ServiceStatus'); }
  async inspect(sourceId: string) {
    const body = parseLiveContract('InspectRequest', { source_id: sourceId });
    if (!this.csrf) await this.control();
    const source = await this.read('/sources/inspect', 'SourceCapability', { method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Live-CSRF': this.csrf! }, body: JSON.stringify(body) });
    if (source.source_id !== sourceId) throw new Error('Foreign selected source identity.');
    return source;
  }
  async replays() {
    const list = await this.read('/replays', 'ReplayList');
    this.recordings.clear();
    for (const entry of list.recordings) if (entry.manifest) this.recordings.set(entry.recording_id, entry.manifest);
    return list;
  }
  private recording(id: string) {
    if (!/^[0-9a-f]{32}$/.test(id)) throw new Error('Invalid recording identity.');
    const manifest = this.recordings.get(id);
    if (!manifest) throw new Error('Refresh recordings before loading this recording.');
    return manifest;
  }
  async replay(id: string) {
    const manifest = this.recording(id);
    const payload = await this.read(`/replays/${id}`, 'ReplayPayload');
    if (payload.manifest.session_id !== manifest.session_id || payload.manifest.generation !== manifest.generation ||
      payload.manifest.events_sha256 !== manifest.events_sha256) throw new Error('Foreign recording identity.');
    return payload;
  }
  async download(id: string): Promise<Blob> {
    const manifest = this.recording(id);
    const response = await this.transport(`/api/live/replays/${id}/download`, { credentials: 'same-origin' });
    if (!response.ok) throw new Error(`Recording download failed (${response.status}).`);
    const original = await response.text();
    const payload = decode('ReplayPayload', original);
    if (payload.manifest.session_id !== manifest.session_id || payload.manifest.generation !== manifest.generation ||
      payload.manifest.events_sha256 !== manifest.events_sha256) throw new Error('Foreign recording identity.');
    // Preserve the verified response text, including IEEE negative zero in raw
    // neural values. JSON.stringify would silently change -0 to +0.
    return new Blob([original], { type: 'application/json' });
  }
  async seek(id: string, tick: number) {
    const manifest = this.recording(id);
    if (!Number.isSafeInteger(tick) || tick < 0 || tick > 6000) throw new Error('Invalid replay tick.');
    const state = await this.read(`/replays/${id}/seek?tick=${tick}`, 'FlightState');
    if (state.snapshot.session_id !== manifest.session_id || state.snapshot.generation !== manifest.generation ||
      state.snapshot.evidence_kind !== manifest.evidence_kind || state.snapshot.tick !== tick) throw new Error('Foreign replay state.');
    return state;
  }
  previewFrame(sessionId: string, generation: number) {
    const target = identity(sessionId, generation);
    return this.read(`/sessions/${target.sessionId}/preview`, 'PreviewReply').then(reply => {
      if (reply.status.session_id !== sessionId || reply.status.generation !== generation) throw new Error('Foreign preview identity.');
      return reply;
    });
  }

  private write(path: string, body: unknown, keepalive = false) {
    if (!this.csrf) throw new Error('Control protection has not been initialized.');
    return this.read(path, 'ApiSnapshot', { method: 'POST', keepalive,
      headers: { 'Content-Type': 'application/json', 'X-Live-CSRF': this.csrf }, body: JSON.stringify(body) });
  }

  /** Call only from an explicit operator action; recording needs per-Start consent. */
  start(config: SessionConfig, recordingConsent = false) {
    const request = parseLiveContract('StartRequest', { schema_version: 'obs-start-1', request_id: token(),
      owner_token: this.ownerToken, config, recording_consent: recordingConsent });
    return this.acquire('/sessions', request, config.source_id);
  }

  preview(sourceId: string, durationSeconds = 15) {
    const request = parseLiveContract('PreviewRequest', { schema_version: 'obs-preview-request-1', request_id: token(),
      owner_token: this.ownerToken, source_id: sourceId, duration_seconds: durationSeconds });
    return this.acquire('/preview', request, sourceId);
  }

  private async acquire(path: string, body: unknown, sourceId: string): Promise<ApiSnapshot> {
    if (this.disposed || this.doc.hidden || this.owner || this.pendingStart) throw new Error('Control tab cannot start another session.');
    this.pendingStart = true;
    this.cancelledStart = false;
    try {
      if (!this.csrf) await this.control();
      if (this.disposed || this.doc.hidden || this.cancelledStart) throw new Error('Start cancelled before capture.');
      const before = this.now();
      const snapshot = await this.write(path, body);
      const target = identity(snapshot.status.session_id, snapshot.status.generation);
      if (this.disposed || this.doc.hidden || this.cancelledStart) {
        void this.write(`/sessions/${target.sessionId}/stop`, { generation: target.generation, owner_token: this.ownerToken }, true).catch(() => {});
        throw new Error('Start completed after the control tab was released.');
      }
      this.closeStream();
      this.watched = target;
      this.watchedSource = sourceId;
      this.flightTick = -1;
      this.sequence = -1;
      this.owner = { ...target, deadline: 0 };
      if (snapshot.kind !== (path === '/preview' ? 'preview' : 'session')) {
        this.release('Unexpected acquired session kind.');
        throw new Error('Unexpected acquired session kind.');
      }
      this.accept(snapshot, target);
      if (!this.owner && !terminal.has(snapshot.status.state)) throw new Error('Acquired session was rejected.');
      if (this.owner) this.scheduleLease(this.owner, snapshot.lease_remaining_ms, this.now() - before);
      return snapshot;
    } finally { this.pendingStart = false; }
  }

  private accept(snapshot: ApiSnapshot, target: Identity) {
    if (!this.watched || !same(this.watched, target) || snapshot.status.session_id !== target.sessionId ||
        snapshot.status.generation !== target.generation || snapshot.event_sequence <= this.sequence) return;
    const source = snapshot.latest_source_frame?.source_id ?? snapshot.last_inferred?.frame.source_id;
    if (source && this.watchedSource && source !== this.watchedSource) {
      this.release('Session source identity changed.'); return;
    }
    if (source) this.watchedSource = source;
    if (snapshot.flight && snapshot.flight.tick < this.flightTick) return;
    if (snapshot.flight) this.flightTick = snapshot.flight.tick;
    this.sequence = snapshot.event_sequence;
    if (terminal.has(snapshot.status.state)) {
      this.clearLease();
      this.owner = null;
      this.closeStream();
      this.options.onNeutral('Session is terminal.');
    }
    this.options.onSnapshot(snapshot);
  }

  /** Passive reconnect: takes a current snapshot; it never Starts or renews. */
  async connect(sessionId: string, generation: number): Promise<void> {
    if (this.disposed) throw new Error('Session client is disposed.');
    const target = identity(sessionId, generation);
    if (this.owner && !same(this.owner, target)) throw new Error('Release current ownership before watching another session.');
    this.closeStream();
    if (!this.watched || !same(this.watched, target)) {
      this.sequence = -1; this.flightTick = -1; this.watchedSource = null;
    }
    this.watched = target;
    const connection = this.connection;
    const stream = this.makeStream(`/api/live/sessions/${sessionId}/events?generation=${generation}`);
    this.stream = stream;
    const current = () => !this.disposed && connection === this.connection && this.stream === stream;
    stream.addEventListener('snapshot', ((event: MessageEvent<string>) => {
      if (!current()) return;
      try { this.accept(decode('ApiSnapshot', event.data), target); }
      catch { this.release('Invalid session stream.'); }
    }) as EventListener);
    stream.addEventListener('error', () => { if (current()) this.release('Session connection lost.'); });
    try {
      const snapshot = await this.read(`/sessions/${sessionId}`, 'ApiSnapshot');
      if (current()) this.accept(snapshot, target);
    } catch (error) {
      if (current()) this.release('Session snapshot unavailable.');
      throw error;
    }
  }

  private scheduleLease(owner: Owner, remainingMs: number, requestElapsedMs: number) {
    if (this.owner !== owner) return;
    this.clearLease();
    // Only response durations are translated to a local deadline. Server and
    // browser monotonic clock origins are unrelated. Subtract full request time
    // conservatively so a delayed response cannot prolong the apparent lease.
    const remaining = Math.max(0, remainingMs - requestElapsedMs);
    owner.deadline = this.now() + remaining;
    if (remaining <= 0) { this.release('Control lease expired.'); return; }
    this.expiry = setTimeout(() => { if (this.owner === owner) this.release('Control lease expired.'); }, remaining);
    this.renewal = setTimeout(() => { void this.renew(owner); }, Math.min(1000, remaining / 2));
  }

  private async renew(owner: Owner) {
    if (this.owner !== owner) return;
    if (this.doc.hidden || this.now() >= owner.deadline) { this.release('Control lease expired.'); return; }
    const before = this.now();
    try {
      const snapshot = await this.write(`/sessions/${owner.sessionId}/renew`, { generation: owner.generation, owner_token: this.ownerToken });
      if (this.owner !== owner) return;
      if (snapshot.status.session_id !== owner.sessionId || snapshot.status.generation !== owner.generation) throw new Error('Foreign renewal identity.');
      this.accept(snapshot, owner);
      if (this.owner === owner) this.scheduleLease(owner, snapshot.lease_remaining_ms, this.now() - before);
    } catch { if (this.owner === owner) this.release('Control renewal failed.'); }
  }

  private clearLease() {
    if (this.renewal !== null) clearTimeout(this.renewal);
    if (this.expiry !== null) clearTimeout(this.expiry);
    this.renewal = this.expiry = null;
  }
  private closeStream() {
    this.connection++;
    this.stream?.close();
    this.stream = null;
  }

  /** Neutralize immediately; a best-effort protected Stop backs the server lease. */
  private release(reason: string) {
    this.cancelledStart = true;
    const owner = this.owner;
    this.owner = null;
    this.clearLease();
    this.closeStream();
    this.watched = null;
    this.watchedSource = null;
    this.options.onNeutral(reason);
    if (owner) void this.write(`/sessions/${owner.sessionId}/stop`, { generation: owner.generation, owner_token: this.ownerToken }, true).catch(() => {});
  }

  stop() { this.release('Control owner stopped.'); }
  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.doc.removeEventListener('visibilitychange', this.visibility);
    this.win.removeEventListener('pagehide', this.pagehide);
    this.release('Control client disposed.');
  }
}
