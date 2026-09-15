"""Private temp-filesystem tests; every observation/response is synthetic."""
import hashlib
import json
import os
import stat

import pytest

from flytrap.live import recording as module
from flytrap.live.contracts import NeuralSample, Provenance, SessionConfig, SourceCapability
from flytrap.live.fixture import fixture_frame
from flytrap.live.flight import FlightAuthority, decode
from flytrap.live.neural import StepResult
from flytrap.live.recording import MANIFEST_RESERVE, RecordingError, RecordingStore
from tests.live.session_fault_worker import result


@pytest.fixture
def sample_record():
    config = SessionConfig(source_id="fixture-pattern", evidence_kind="fixture", seed=3,
                           recording=True, duration_seconds=2)
    source = SourceCapability(schema_version="obs-source-1", source_id=config.source_id,
        evidence_kind="fixture", name="Synthetic private storage test", driver=None, backend="synthetic",
        capabilities=None, formats=None, metadata_state="available", producer_detection="synthetic")
    provenance = Provenance(source_head="a"*40, source_tree_sha256="b"*64, graph_sha256="c"*64,
        annotations_sha256="d"*64, checkpoint_sha256="e"*64, model_source_sha256="f"*64,
        model_config_sha256="a"*64, backend_version="synthetic-1", python_version="3.14.7",
        numpy_version="fixture", scipy_version="fixture", model_id="fixture-storage",
        neural_state_mode="windowed_reset", gains="all-one-float32", learning_enabled=False)
    flight = FlightAuthority("fixture-storage", 1, "fixture", origin_ms=100.)
    frame = fixture_frame(0, "fixture-storage", 1, receipt_monotonic_ms=100.).identity
    worker = result({"session_id": "fixture-storage", "generation": 1}, {"step_index": 0})
    worker["completed_monotonic_ms"] = 101.
    worker = StepResult.model_validate(worker)
    sample = NeuralSample(schema_version="obs-neural-1", response_id="sample-0", frame=frame,
        observation_u8=list(range(256)), encoder_id=config.encoder.encoder_id, model_id=provenance.model_id,
        step_index=0, completed_monotonic_ms=101., neural_ms=20., neural_state_mode="windowed_reset",
        motor_rates_hz=worker.motor_rates_hz, raw_action=worker.raw_action)
    return config, source, provenance, flight, sample, worker


def write_record(store, fixture):
    config, source, provenance, flight, sample, worker = fixture
    writer = store.start(config, source, provenance, flight.initial)
    writer.append_input(sample.frame, sample.observation_u8, sample.step_index)
    writer.append_sample(sample, worker)
    controls = decode(sample.motor_rates_hz, response_id=sample.response_id,
        session_id=sample.frame.session_id, generation=1, evidence_kind="fixture", receipt_ms=100.,
        completed_ms=101., now_ms=102.)
    flight.apply(controls, now_ms=102.)
    flight.advance_to(1100.)
    flight.stop()
    writer.finish(flight.trace(), flight.current)
    return writer


def test_exact_roundtrip_private_permissions_seek_and_terminal(tmp_path, sample_record):
    store = RecordingStore(tmp_path / "private")
    writer = write_record(store, sample_record)
    restored = RecordingStore(store.root).read(writer.recording_id)
    assert restored.manifest.state == "complete"
    assert restored.inputs[0].observation_u8 == list(range(256))
    assert restored.samples == [sample_record[4]]
    assert restored.results == [sample_record[5]]
    assert restored.trace == sample_record[3].trace()
    assert restored.seek(0) == sample_record[3].initial
    assert restored.seek(50) == sample_record[3].current
    assert restored.seek(25).snapshot.position != restored.seek(0).snapshot.position
    assert restored.seek(50).snapshot.neutral
    assert stat.S_IMODE(store.root.stat().st_mode) == 0o700
    assert stat.S_IMODE(writer.directory.stat().st_mode) == 0o700
    for path in writer.directory.iterdir():
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert {p.name for p in writer.directory.iterdir()} == {"manifest.json", "events.jsonl", "complete.sha256"}
    assert sum(p.stat().st_size for p in writer.directory.iterdir()) <= sample_record[0].recording_max_bytes
    with pytest.raises(RecordingError):
        restored.seek(51)
    with pytest.raises(RecordingError):
        restored.seek(True)


def test_recording_off_creates_nothing(tmp_path, sample_record):
    store = RecordingStore(tmp_path / "private")
    assert store.list() == [] and not store.root.exists()
    config, source, provenance, flight, *_ = sample_record
    with pytest.raises(RecordingError, match="opt-in"):
        store.start(config.model_copy(update={"recording": False}), source, provenance, flight.initial)
    assert not store.root.exists()


def test_reservation_startup_failure_is_explicitly_aborted(tmp_path, sample_record):
    config, source, _, flight, *_ = sample_record
    store = RecordingStore(tmp_path / "private")
    reservation = store.reserve(config, source, flight.initial.snapshot.session_id, 1)
    assert store.list() == [{"recording_id": reservation.recording_id, "state": "partial"}]
    reservation.abort()
    assert store.list() == [{"recording_id": reservation.recording_id, "state": "aborted"}]
    with pytest.raises((OSError, ValueError)):
        store.read(reservation.recording_id)


def test_reservation_initializes_same_private_id(tmp_path, sample_record):
    config, source, provenance, flight, *_ = sample_record
    store = RecordingStore(tmp_path / "private")
    reservation = store.reserve(config, source, flight.initial.snapshot.session_id, 1)
    writer = reservation.initialize(provenance, flight.initial)
    assert writer.recording_id == reservation.recording_id
    assert not (writer.directory / "reservation.json").exists()
    writer.finish(flight.trace(), flight.current)
    assert store.read(writer.recording_id).seek(0) == flight.current


@pytest.mark.parametrize("recording_id", ["../secret", "a/../b", "/etc/passwd", "", "A"*32, "a"*33])
def test_traversal_ids_rejected(tmp_path, recording_id):
    with pytest.raises(RecordingError):
        RecordingStore(tmp_path).read(recording_id)


def test_symlink_and_public_permissions_rejected(tmp_path, sample_record):
    store = RecordingStore(tmp_path / "private")
    writer = write_record(store, sample_record)
    path = writer.directory / "events.jsonl"
    original = path.read_bytes()
    path.unlink()
    target = tmp_path / "external"
    target.write_bytes(original)
    path.symlink_to(target)
    with pytest.raises((RecordingError, OSError)):
        store.read(writer.recording_id)
    path.unlink()
    path.write_bytes(original)
    path.chmod(0o644)
    with pytest.raises(RecordingError, match="permissions"):
        store.read(writer.recording_id)
    linked = tmp_path / "linked"
    linked.symlink_to(store.root, target_is_directory=True)
    with pytest.raises(RecordingError, match="symlink"):
        RecordingStore(linked).read(writer.recording_id)


@pytest.mark.parametrize("file", ["manifest.json", "events.jsonl"])
def test_raw_corruption_rejected(tmp_path, sample_record, file):
    store = RecordingStore(tmp_path / "private")
    writer = write_record(store, sample_record)
    path = writer.directory / file
    payload = path.read_bytes().replace(b'synthetic-1', b'synthetic-2', 1) if file == 'manifest.json' else (
        path.read_bytes().replace(b'fixture-storage', b'fixture-altered', 1))
    path.write_bytes(payload)
    with pytest.raises(RecordingError, match="hash"):
        store.read(writer.recording_id)


def rewrite_checked(writer, mutate_manifest=None, mutate_events=None):
    """Rehash malicious edits to exercise semantic checks beyond checksums."""
    envelope = json.loads((writer.directory / "manifest.json").read_text())
    if mutate_events:
        events = [json.loads(line) for line in (writer.directory / "events.jsonl").read_text().splitlines()]
        mutate_events(events)
        data = b"".join(module._json(event)+b"\n" for event in events)
        (writer.directory / "events.jsonl").write_bytes(data)
        envelope["manifest"].update(events_bytes=len(data), events_sha256=hashlib.sha256(data).hexdigest(),
                                     event_count=len(events))
    if mutate_manifest:
        mutate_manifest(envelope["manifest"])
    envelope["sha256"] = hashlib.sha256(module._json({"recording_id": envelope["recording_id"],
                                                     "manifest": envelope["manifest"]})).hexdigest()
    (writer.directory / "manifest.json").write_bytes(module._json(envelope))
    (writer.directory / "complete.sha256").write_bytes(hashlib.sha256(module._json(envelope)).hexdigest().encode())


@pytest.mark.parametrize("mutation", [
    lambda m: m.update(schema_version="obs-replay-99"),
    lambda m: m.update(events_file="../events.jsonl"),
    lambda m: m["config"].update(source_id="other-source"),
    lambda m: m["provenance"].update(model_id="other-model"),
    lambda m: m["initial_flight"].update(generation=2),
])
def test_rehashed_invalid_manifest_rejected(tmp_path, sample_record, mutation):
    store = RecordingStore(tmp_path / "private")
    writer = write_record(store, sample_record)
    rewrite_checked(writer, mutate_manifest=mutation)
    with pytest.raises(ValueError):
        store.read(writer.recording_id)


@pytest.mark.parametrize("mutation", [
    lambda e: e[0]["observation_u8"].__setitem__(0, 32),
    lambda e: e[0]["frame"].update(source_id="other-source"),
    lambda e: e[1]["sample"].update(step_index=1),
    lambda e: e[1]["result"]["raw_action"].update(dx=99.),
    lambda e: e[2]["trace"]["events"][0]["controls"].update(speed_target_units_s=5.),
    lambda e: e[2]["trace"].update(schema_version="obs-flight-trace-99"),
    lambda e: e[2]["final"]["snapshot"]["position"].__setitem__(0, 999.),
    lambda e: e.reverse(),
    lambda e: e.pop(),
])
def test_rehashed_invalid_event_metadata_and_physics_rejected(tmp_path, sample_record, mutation):
    store = RecordingStore(tmp_path / "private")
    writer = write_record(store, sample_record)
    rewrite_checked(writer, mutate_events=mutation)
    with pytest.raises(ValueError):
        store.read(writer.recording_id)


def test_partial_and_byte_limit_never_complete(tmp_path, sample_record):
    config, source, provenance, flight, sample, _ = sample_record
    store = RecordingStore(tmp_path / "private")
    config = config.model_copy(update={"recording_max_bytes": MANIFEST_RESERVE + 32})
    writer = store.start(config, source, provenance, flight.initial)
    assert store.manifest(writer.recording_id).state == "partial"
    with pytest.raises(RecordingError, match="partial"):
        store.read(writer.recording_id)
    with pytest.raises(RecordingError, match="cap"):
        writer.append_input(sample.frame, sample.observation_u8, 0)
    assert store.manifest(writer.recording_id).state == "aborted"
    assert sum(p.stat().st_size for p in writer.directory.iterdir()) < config.recording_max_bytes


@pytest.mark.parametrize("fault", ["write", "fsync", "replace"])
def test_disk_fault_never_publishes_complete(tmp_path, sample_record, monkeypatch, fault):
    config, source, provenance, flight, sample, _ = sample_record
    store = RecordingStore(tmp_path / "private")
    writer = store.start(config, source, provenance, flight.initial)

    def fail(*args, **kwargs):
        raise OSError("synthetic disk failure")

    with monkeypatch.context() as patch:
        patch.setattr(os, fault, fail)
        with pytest.raises(OSError):
            writer.append_input(sample.frame, sample.observation_u8, 0)
    assert store.manifest(writer.recording_id).state in ("partial", "aborted")
    assert "complete" not in (writer.directory / "manifest.json").read_text()
    with pytest.raises(RecordingError):
        store.read(writer.recording_id)


def test_failed_final_verification_stays_aborted(tmp_path, sample_record):
    config, source, provenance, flight, *_ = sample_record
    store = RecordingStore(tmp_path / "private")
    writer = store.start(config, source, provenance, flight.initial)
    invalid_final = flight.current.model_copy(update={"snapshot": flight.current.snapshot.model_copy(
        update={"position": [999., 0., 2.]})})
    with pytest.raises(RecordingError, match="disagrees"):
        writer.finish(flight.trace(), invalid_final)
    assert store.manifest(writer.recording_id).state == "aborted"


def test_replay_opens_no_devices_calls_no_model_and_preserves_ledgers(tmp_path, sample_record, monkeypatch):
    from flytrap.live.capture import Capture
    from flytrap.live.accounting import LiveLedger
    from flytrap.controllers.fly import FlyController

    store = RecordingStore(tmp_path / "private")
    writer = write_record(store, sample_record)
    ledger = tmp_path / "attempts.jsonl"
    ledger.write_bytes(b'{"fixture_attempts":7}\n')
    before = ledger.read_bytes()

    def forbidden(*args, **kwargs):
        pytest.fail("replay touched a source, model or call ledger")

    monkeypatch.setattr(Capture, "start", forbidden)
    monkeypatch.setattr(FlyController, "__init__", forbidden)
    monkeypatch.setattr(LiveLedger, "record_attempt", forbidden)
    native_open = os.open
    opened = []

    def checked_open(path, *args, **kwargs):
        opened.append(str(path))
        assert not str(path).startswith("/dev/")
        return native_open(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", checked_open)
    for _ in range(2):
        restored = store.read(writer.recording_id)
        for tick in (0, 49, 20, 50, 0):
            assert restored.seek(tick).snapshot.tick == tick
    assert len(opened) == 6 and ledger.read_bytes() == before


@pytest.mark.parametrize("fault_point", [1, 2, 3, 4, 5, 6])
def test_final_publication_fsync_fault_has_no_replayable_complete(tmp_path, sample_record, monkeypatch, fault_point):
    config, source, provenance, flight, *_ = sample_record
    store = RecordingStore(tmp_path / "private")
    writer = store.start(config, source, provenance, flight.initial)
    fsync = os.fsync
    calls = 0

    def fail_once(fd):
        nonlocal calls
        calls += 1
        if calls == fault_point:
            raise OSError("synthetic finalization fsync failure")
        return fsync(fd)

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", fail_once)
        with pytest.raises(OSError):
            writer.finish(flight.trace(), flight.current)
    assert calls >= fault_point
    assert not (writer.directory / "complete.sha256").exists()
    assert store.manifest(writer.recording_id).state == "aborted"
    with pytest.raises(RecordingError):
        store.read(writer.recording_id)


def test_truncated_event_and_missing_completion_seal_fail_closed(tmp_path, sample_record):
    store = RecordingStore(tmp_path / "private")
    writer = write_record(store, sample_record)
    events = writer.directory / "events.jsonl"
    events.write_bytes(events.read_bytes()[:-1])
    with pytest.raises(RecordingError):
        store.read(writer.recording_id)
    (writer.directory / "complete.sha256").unlink()
    with pytest.raises((OSError, RecordingError)):
        store.read(writer.recording_id)
    assert "error" in store.list()[0]


def test_list_verifies_events_before_displaying_complete_and_payload_is_bounded(tmp_path, sample_record):
    store = RecordingStore(tmp_path / "private")
    writer = write_record(store, sample_record)
    restored = store.read(writer.recording_id)
    payload = restored.payload()
    assert payload.final == restored.seek(50)
    assert payload.results == [sample_record[5]]
    assert "states" not in payload.model_dump()
    listing = module.ReplayList(recordings=store.list())
    assert listing.recordings[0].manifest.state == "complete"
    events = writer.directory / "events.jsonl"
    events.write_bytes(events.read_bytes()[:-1])
    assert store.list() == [{"recording_id": writer.recording_id,
                             "error": "Recording unavailable or corrupted."}]
    with pytest.raises(ValueError):
        module.ReplayListEntry(recording_id=writer.recording_id, manifest=writer.manifest, state="partial")


def test_listing_bounded_directory_enumeration(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    for index in range(129):
        (root / f"{index:032x}").mkdir(mode=0o700)
    with pytest.raises(RecordingError, match="128"):
        RecordingStore(root).list()


def test_reservation_transition_failure_closes_writer(tmp_path, sample_record, monkeypatch):
    from pathlib import Path
    config, source, provenance, flight, *_ = sample_record
    store = RecordingStore(tmp_path / "private")
    reservation = store.reserve(config, source, flight.initial.snapshot.session_id, 1)
    original_unlink, original_abort = Path.unlink, module.Recorder.abort
    closed = []

    def fail_reservation_unlink(path, *args, **kwargs):
        if path.name == "reservation.json":
            raise OSError("synthetic reservation unlink failure")
        return original_unlink(path, *args, **kwargs)

    def tracked_abort(writer):
        original_abort(writer)
        with pytest.raises(OSError):
            os.fstat(writer._fd)
        closed.append(writer._closed)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", fail_reservation_unlink)
        patch.setattr(module.Recorder, "abort", tracked_abort)
        with pytest.raises(OSError, match="unlink failure"):
            reservation.initialize(provenance, flight.initial)
    assert closed == [True]
    assert store.manifest(reservation.recording_id).state == "aborted"


def test_intact_complete_record_transplanted_to_another_id_is_rejected(tmp_path, sample_record):
    import shutil
    import uuid
    store = RecordingStore(tmp_path / "private")
    writer = write_record(store, sample_record)
    transplanted_id = uuid.uuid4().hex
    transplanted = store.root / transplanted_id
    shutil.copytree(writer.directory, transplanted)
    assert (transplanted / "events.jsonl").read_bytes() == (writer.directory / "events.jsonl").read_bytes()
    assert store.read(writer.recording_id).manifest.state == "complete"
    with pytest.raises(RecordingError, match="directory identity"):
        store.read(transplanted_id)
    listing = {entry["recording_id"]: entry for entry in store.list()}
    assert "error" in listing[transplanted_id]
    assert listing[writer.recording_id]["manifest"].state == "complete"


def test_intact_reservation_transplanted_to_another_id_is_rejected(tmp_path, sample_record):
    import shutil
    import uuid
    config, source, _, flight, *_ = sample_record
    store = RecordingStore(tmp_path / "private")
    reservation = store.reserve(config, source, flight.initial.snapshot.session_id, 1)
    transplanted_id = uuid.uuid4().hex
    shutil.copytree(reservation.directory, store.root / transplanted_id)
    listing = {entry["recording_id"]: entry for entry in store.list()}
    assert listing[reservation.recording_id]["state"] == "partial"
    assert "error" in listing[transplanted_id]
    reservation.abort()


def test_oversized_reservation_rejected_before_writing_bytes(tmp_path, sample_record):
    config, source, _, flight, *_ = sample_record
    config = config.model_copy(update={"recording_max_bytes": MANIFEST_RESERVE})
    source = SourceCapability.model_validate({**source.model_dump(), "formats": [
        {"pixel_format": "MJPEG", "width": 8192, "height": 8192, "fps": 240.}
    ] * 128})
    store = RecordingStore(tmp_path / "private")
    with pytest.raises(RecordingError, match="reservation byte cap"):
        store.reserve(config, source, flight.initial.snapshot.session_id, 1)
    assert all(not list(directory.iterdir()) for directory in store.root.iterdir())


def test_atomic_transition_peak_includes_reservation_manifest_temps_and_seal(tmp_path, sample_record, monkeypatch):
    config, source, provenance, flight, sample, worker = sample_record
    config = config.model_copy(update={"recording_max_bytes": MANIFEST_RESERVE + 8192})
    store = RecordingStore(tmp_path / "private")
    replace = os.replace
    peaks = []

    def observe_before_replace(src, dst):
        directory = src.parent
        sizes = {path.name: path.stat().st_size for path in directory.iterdir()}
        assert sum(sizes.values()) <= config.recording_max_bytes
        peaks.append(sizes)
        return replace(src, dst)

    monkeypatch.setattr(os, "replace", observe_before_replace)
    reservation = store.reserve(config, source, flight.initial.snapshot.session_id, 1)
    writer = reservation.initialize(provenance, flight.initial)
    writer.append_input(sample.frame, sample.observation_u8, 0)
    writer.append_sample(sample, worker)
    writer.finish(flight.trace(), flight.current)
    assert store.read(writer.recording_id).manifest.state == "complete"
    assert any({"reservation.json", "manifest.json.tmp", "events.jsonl"} <= set(peak) for peak in peaks)
    assert any({"manifest.json", "manifest.json.tmp", "events.jsonl"} <= set(peak) for peak in peaks)
    assert any({"manifest.json", "events.jsonl", "complete.sha256.tmp"} <= set(peak) for peak in peaks)
