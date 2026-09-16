"""Synthetic ground repair replay evidence; never captures pixels or runs inference."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from fastapi.testclient import TestClient
import pytest

from flytrap.live.api import create_live_app
from flytrap.live.contracts import GROUND_ENVIRONMENT, MotorRates
from flytrap.live.flight import FlightAuthority, FlightState, decode
from flytrap.live.recording import RecordingStore, ReplayPayload
from flytrap.live.service import LiveService
from tests.live.test_recording import rewrite_checked


FROZEN = Path(__file__).parents[1] / "fixtures/live/v1-below-ground"
FIXTURE = json.loads((FROZEN / "fixture.json").read_text())


@pytest.fixture
def historical_store(tmp_path):
    """Copy sealed v1 bytes unchanged; git does not retain private file modes."""
    root = tmp_path / "historical"
    root.mkdir(mode=0o700)
    target = root / FIXTURE["recording_id"]
    shutil.copytree(FROZEN / FIXTURE["recording_id"], target)
    target.chmod(0o700)
    for path in target.iterdir():
        path.chmod(0o600)
    return RecordingStore(root)


def test_frozen_v1_descends_below_ground_and_preserves_original_hashes(historical_store):
    identity = FIXTURE["recording_id"]
    directory = historical_store.root / identity
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    assert {name: hashlib.sha256(data).hexdigest() for name, data in before.items()} == FIXTURE["files"]
    restored = historical_store.read(identity)
    assert restored.trace.initial.physics_id == "flight-fixed20-v1"
    assert restored.seek(600).snapshot.position == FIXTURE["final_position"]
    assert restored.seek(600).snapshot.position[2] < -4.
    assert restored.seek(0).snapshot.position == [0., 0., 2.]
    payload = restored.payload().model_dump(mode="json")
    assert "environment" not in payload["manifest"]["initial_flight"]
    assert "ground_contact" not in payload["final"]["snapshot"]
    assert "physics_id" not in payload["manifest"]["initial_flight"]
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == before


def ground_recording(tmp_path, historical_store):
    """A new synthetic trajectory, using only fabricated response metadata."""
    original = historical_store.read(FIXTURE["recording_id"])
    store = RecordingStore(tmp_path / "ground")
    flight = FlightAuthority(original.manifest.session_id, 1, "fixture", origin_ms=0.)
    writer = store.start(original.manifest.config, original.manifest.source,
                         original.manifest.provenance, flight.initial)
    live = [flight.initial]
    for second, (sample, worker) in enumerate(zip(original.samples, original.results, strict=True)):
        # Eight seconds descending/contact, then four seconds commanded ascent.
        rates = MotorRates(steer_L=125., steer_R=0., fwd_L=0. if second < 8 else 1000.,
                           fwd_R=0. if second < 8 else 1000., back=1000. if second < 8 else 0.,
                           stop=0., click=0.)
        sample = sample.model_copy(update={"motor_rates_hz": rates})
        worker = worker.model_copy(update={"motor_rates_hz": rates})
        writer.append_input(sample.frame, sample.observation_u8, sample.step_index)
        writer.append_sample(sample, worker)
        stamp = float(second*1000)
        controls = decode(rates, response_id=sample.response_id, session_id=sample.frame.session_id,
                          generation=1, evidence_kind="fixture", receipt_ms=stamp,
                          completed_ms=stamp, now_ms=stamp)
        flight.apply(controls, now_ms=stamp)
        for tick in range(second*50+1, (second+1)*50+1):
            flight.advance_to(float(tick*20))
            live.append(flight.current)
    flight.stop()
    live[-1] = flight.current
    writer.finish(flight.trace(), flight.current)
    return store, writer, live


def test_ground_live_serialized_replay_and_every_seek_are_exact(tmp_path, historical_store):
    store, writer, live = ground_recording(tmp_path, historical_store)
    restored = store.read(writer.recording_id)
    assert restored.manifest.provenance == historical_store.read(FIXTURE["recording_id"]).manifest.provenance
    assert restored.trace.initial.physics_id == "flight-fixed20-ground-v2"
    contact = [state for state in live if state.snapshot.ground_contact]
    minimum = GROUND_ENVIRONMENT.ground_z + GROUND_ENVIRONMENT.clearance
    assert contact and all(state.snapshot.position[2] >= minimum for state in live)
    assert live[-1].snapshot.position[2] > contact[-1].snapshot.position[2]
    assert all(state.velocity[2] == 0. for state in contact)
    for tick, state in enumerate(live):
        assert FlightState.model_validate_json(state.model_dump_json()) == state
        assert restored.seek(tick) == state
    assert ReplayPayload.model_validate_json(restored.payload().model_dump_json()).final == live[-1]


@pytest.mark.parametrize("version", ["historical", "ground"])
def test_actual_http_replay_download_and_seek_are_read_only(tmp_path, historical_store, monkeypatch, version):
    if version == "ground":
        store, writer, live = ground_recording(tmp_path, historical_store)
        identity = writer.recording_id
    else:
        store, identity = historical_store, FIXTURE["recording_id"]
        live = store.read(identity).states
    before = {p.name: p.read_bytes() for p in (store.root / identity).iterdir()}

    def forbidden(*args, **kwargs):
        pytest.fail("read-only replay must not spawn capture or inference")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    service = LiveService(repository_root=tmp_path, recording_store=store)
    with TestClient(create_live_app(dist=tmp_path, service=service), base_url="http://127.0.0.1") as client:
        endpoint = f"/api/live/replays/{identity}"
        response = client.get(endpoint)
        assert response.status_code == 200
        payload = ReplayPayload.model_validate(response.json())
        assert payload.final == live[-1]
        download = client.get(endpoint + "/download")
        assert download.status_code == 200 and download.json() == response.json()
        assert client.get("/api/live/replays").json()["recordings"][0]["manifest"] == response.json()["manifest"]
        for tick in (0, 50, 150, 350, 400, 450, 600, 200, 0):
            seek = client.get(endpoint + "/seek", params={"tick": tick})
            assert seek.status_code == 200
            assert FlightState.model_validate(seek.json()) == live[tick]
    assert {p.name: p.read_bytes() for p in (store.root / identity).iterdir()} == before


@pytest.mark.parametrize("mutation", [
    lambda e: e[-1]["trace"]["initial"].update(physics_id="flight-fixed20-v1"),
    lambda e: e[-1]["final"].update(physics_id="flight-fixed20-v1"),
    lambda e: e[-1]["final"]["snapshot"].update(physics_id="flight-future-99"),
    lambda e: e[-1]["trace"]["initial"]["snapshot"]["environment"].update(ground_z=-40.),
    lambda e: e[-1]["final"]["snapshot"]["environment"].update(clearance=0.),
])
def test_rehashed_ground_identity_or_collision_mismatch_is_rejected(tmp_path, historical_store, mutation):
    store, writer, _ = ground_recording(tmp_path, historical_store)
    rewrite_checked(writer, mutate_events=mutation)
    with pytest.raises(ValueError):
        store.read(writer.recording_id)


def test_original_browser_v1_fixture_remains_readable():
    path = Path(__file__).parents[2] / "web/tests/fixtures/recorded-flight.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "40a595693e88eae203ef658991fdf6ea4d4c711237c169fd40487c0d00ef6975"
    payload = ReplayPayload.model_validate_json(path.read_bytes())
    assert payload.trace.initial.physics_id == "flight-fixed20-v1"
