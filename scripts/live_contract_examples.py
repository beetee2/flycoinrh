"""Declared synthetic wire corpus, shared by Python and browser validators."""
import json
import base64
from io import BytesIO

from PIL import Image

from flytrap.live.contracts import EncoderConfig, GROUND_ENVIRONMENT, LiveConfig, LiveHealth, SessionConfig
from flytrap.live.api_contracts import ControlBootstrap


def corpus():
    identity = dict(session_id="fixture-session", generation=1, evidence_kind="fixture")
    frame = dict(schema_version="obs-frame-1", **identity, source_id="fixture-source", sequence=7,
                 width=640, height=480, pixel_format="RGB24", receipt_monotonic_ms=100.0,
                 source_timestamp_ms=None, source_sequence=None, source_clock="unknown")
    source = dict(schema_version="obs-source-1", source_id="fixture-source", evidence_kind="fixture",
                  name="SYNTHETIC test source", driver=None, backend="synthetic", capabilities=None,
                  formats=None, metadata_state="partial", producer_detection="synthetic")
    sample = dict(schema_version="obs-neural-1", response_id="response-1", frame=frame,
                  observation_u8=[i % 256 for i in range(256)], encoder_id="obs-rgb-letterbox16-v1",
                  model_id="fixture-model", step_index=0, completed_monotonic_ms=200.0, neural_ms=20.0,
                  neural_state_mode="windowed_reset", motor_rates_hz=dict.fromkeys(
                      ["steer_L", "steer_R", "fwd_L", "fwd_R", "back", "stop", "click"], 0.0),
                  raw_action=dict(dx=0.0, dy=0.0, click=False))
    controls = dict(schema_version="obs-controls-1", decoder_id="motor-flight-v1", **identity,
                    response_id="response-1", issued_monotonic_ms=200.0, expires_monotonic_ms=2100.0,
                    yaw_rate_rad_s=0.0, pitch_target_rad=0.0, speed_target_units_s=0.0)
    flight = dict(schema_version="obs-flight-1", **identity, tick=0, position=[0.0]*3,
                  yaw_rad=0.0, pitch_rad=0.0, speed_units_s=0.0, applied_response_id=None, neutral=True)
    config = SessionConfig(source_id="fixture-source", evidence_kind="fixture", seed=17).model_dump()
    status = dict(schema_version="obs-session-status-1", **identity, state="idle", reason=None,
                  attempted_calls=0, accepted_frames=0, overwritten_frames=0, content_unchanged_ms=0.0,
                  producer_health="unknown", last_frame_sequence=None, last_response_id=None)
    stream = dict(schema_version="obs-stream-1", event_sequence=0, sent_monotonic_ms=200.0,
                  status=status, latest_source_frame=frame, neural_sample=sample, flight=flight)
    provenance = dict.fromkeys(["source_tree_sha256", "graph_sha256", "annotations_sha256",
                               "checkpoint_sha256", "model_source_sha256", "model_config_sha256"], "0"*64)
    provenance.update(source_head="0"*40, backend_version="synthetic", python_version="test",
                      numpy_version="test", scipy_version="test", model_id="fixture-model",
                      neural_state_mode="windowed_reset", gains="all-one-float32", learning_enabled=False)
    replay = dict(schema_version="obs-replay-1", **identity, state="partial", config={**config, "recording": True},
                  source=source, initial_flight=flight, provenance=provenance, events_sha256="0"*64,
                  event_count=0, events_bytes=0, events_file="events.jsonl")
    good = dict(SourceCapability=source, FrameIdentity=frame, EncoderConfig=EncoderConfig().model_dump(),
                NeuralSample=sample, FlightControls=controls, FlightSnapshot=flight, SessionConfig=config,
                SessionStatus=status, StreamEnvelope=stream, ReplayManifest=replay,
                LiveHealth=LiveHealth().model_dump(), LiveConfig=LiveConfig().model_dump(),
                SyntheticFlightPreview=dict(schema_version="obs-flight-preview-1", evidence_kind="synthetic",
                    dt_ms=20, snapshots=[flight, {**flight, "tick": 1}]))
    api_snapshot = {**stream, "schema_version": "obs-api-snapshot-1", "kind": "session",
        "lease_remaining_ms": 2000., "source_receipt_age_ms": 100., "response_age_ms": 100.,
        "last_inferred": sample, "completed_calls": 1, "rejected_results": 0,
        "model_hz": 1., "capture_hz": 30., "model_mode": "fixture",
        "last_step_wall_ms": 100., "recording_id": None, "recording_state": "off"}
    preview_image = dict(frame=frame, width=1, height=1, rgb_base64=base64.b64encode(bytes(3)).decode(),
                         observation_u8=sample["observation_u8"])
    good.update(StartRequest=dict(schema_version="obs-start-1", request_id="1"*32, owner_token="2"*32,
                                 config=config, recording_consent=False),
        OwnerRequest=dict(generation=1, owner_token="2"*32),
        PreviewRequest=dict(schema_version="obs-preview-request-1", request_id="1"*32, owner_token="2"*32,
                            source_id=source["source_id"], duration_seconds=15),
        SourceList=dict(schema_version="obs-sources-1", sources=[source]),
        ControlBootstrap=ControlBootstrap(csrf_token="1"*32+"."+"2"*64).model_dump(),
        SourcePreview=preview_image, ApiSnapshot=api_snapshot,
        ServiceStatus=dict(schema_version="obs-service-status-1", current=api_snapshot),
        PreviewReply=dict(schema_version="obs-source-preview-1", status=status, latest=preview_image),
        ReplayList=dict(schema_version="obs-replay-list-1", recordings=[]),
        FlightState=dict(physics_id="flight-fixed20-v1", snapshot=flight, velocity=[0., 0., 0.], yaw_rate=0.))
    with BytesIO() as output, Image.new("RGB", (4, 3), "ivory") as image:
        image.save(output, format="JPEG", quality=85)
        jpeg = output.getvalue()
    display = dict(schema_version="screen-gremlin-display-1", frame=frame, width=4, height=3,
        mime_type="image/jpeg", jpeg_base64=base64.b64encode(jpeg).decode(), encoded_bytes=len(jpeg),
        delivered_monotonic_ms=200., receipt_age_ms=100.)
    display_reply = dict(schema_version="screen-gremlin-display-reply-1",
                         status={**status, "state": "previewing"}, latest=display)
    good.update(DisplayFrame=display, DisplayReply=display_reply)
    cases = [dict(name=f"{name} valid synthetic", contract=name, valid=True, value=value)
             for name, value in good.items()]
    for label, patch in (
        ("oversized width", {"width": 961}),
        ("oversized encoded image", {"encoded_bytes": 262145}),
        ("invalid JPEG", {"jpeg_base64": "AAAA", "encoded_bytes": 4}),
        ("incorrect dimensions", {"width": 3}),
        ("unknown field", {"caption": "never enters this protocol"}),
        ("unknown version", {"schema_version": "screen-gremlin-display-99"}),
        ("delivery predates capture", {"delivered_monotonic_ms": 0.}),
    ):
        cases.append(dict(name=f"DisplayFrame {label}", contract="DisplayFrame", valid=False,
                          value={**display, **patch}))
    for label, patch in (
        ("foreign session", {"session_id": "foreign"}),
        ("foreign generation", {"generation": 2}),
        ("inactive session", {"state": "stopped"}),
    ):
        cases.append(dict(name=f"DisplayReply {label}", contract="DisplayReply", valid=False,
            value={**display_reply, "status": {**display_reply["status"], **patch}}))
    cases.append(dict(name="real source metadata shape only, no hardware evidence", contract="SourceCapability",
                      valid=True, value={**source, "evidence_kind": "real", "backend": "ffmpeg-v4l2",
                                         "producer_detection": "unknown"}))
    cases.append(dict(name="explicit producer clock on synthetic frame", contract="FrameIdentity", valid=True,
                      value={**frame, "source_clock": "producer", "source_timestamp_ms": 12.0,
                             "source_sequence": 3}))

    ground = {**flight, "schema_version": "obs-flight-2", "physics_id": "flight-fixed20-ground-v2",
              "environment": GROUND_ENVIRONMENT.model_dump(), "ground_contact": False}
    ground_state = {**good["FlightState"], "physics_id": ground["physics_id"], "snapshot": ground}
    for name, value in (
        ("GroundEnvironment", GROUND_ENVIRONMENT.model_dump()),
        ("GroundFlightSnapshot", ground),
        ("FlightState", ground_state),
        ("StreamEnvelope", {**stream, "flight": ground}),
        ("ApiSnapshot", {**api_snapshot, "flight": ground}),
        ("ReplayManifest", {**replay, "initial_flight": ground}),
        ("SyntheticFlightPreview", {**good["SyntheticFlightPreview"],
                                    "snapshots": [ground, {**ground, "tick": 1}]}),
    ):
        cases.append(dict(name=f"{name} ground v2 synthetic", contract=name, valid=True, value=value))
    for name, value, label in (
        ("GroundEnvironment", {**GROUND_ENVIRONMENT.model_dump(), "ground_z": -40.}, "conflicting plane"),
        ("GroundEnvironment", {**GROUND_ENVIRONMENT.model_dump(), "clearance": 0.}, "conflicting clearance"),
        ("GroundEnvironment", {**GROUND_ENVIRONMENT.model_dump(), "environment_id": "future-99"}, "unknown environment"),
        ("GroundFlightSnapshot", {**ground, "physics_id": "flight-fixed20-v1"}, "legacy identity on ground pose"),
        ("GroundFlightSnapshot", {**ground, "position": [0., 0., -4.]}, "ground pose penetrates clearance"),
        ("GroundFlightSnapshot", {**ground, "ground_contact": True}, "contact above plane"),
        ("FlightState", {**ground_state, "physics_id": "flight-fixed20-v1"}, "state and snapshot physics mismatch"),
        ("FlightState", {**ground_state, "snapshot": flight}, "ground state with legacy snapshot"),
        ("SyntheticFlightPreview", {**good["SyntheticFlightPreview"], "snapshots": [flight, {**ground, "tick": 1}]},
         "mixed physics preview"),
    ):
        cases.append(dict(name=label, contract=name, valid=False, value=value))

    def bad(name, path, value, label):
        # A JSON round trip breaks template object aliases: changing the latest
        # source frame must not also change the recorded neural frame.
        obj = json.loads(json.dumps(good[name]))
        parent = obj
        parts = path.split(".")
        for part in parts[:-1]:
            parent = parent[int(part)] if isinstance(parent, list) else parent[part]
        parent[parts[-1]] = value
        cases.append(dict(name=label, contract=name, valid=False, value=obj))

    for name in good:
        bad(name, "unrecognized", "forbidden", f"{name} unknown field")
        bad(name, "schema_version", "future-999", f"{name} unknown version")
    for name, path, value, label in [
        ("SourceCapability", "evidence_kind", "real", "synthetic source relabeled real"),
        ("SourceCapability", "backend", "ffmpeg-v4l2", "fixture source with real backend"),
        ("SourceCapability", "producer_detection", "driver", "fixture source with real detection"),
        ("FrameIdentity", "generation", 0, "zero epoch"),
        ("FrameIdentity", "sequence", True, "bool sequence"),
        ("FrameIdentity", "sequence", "7", "string sequence"),
        ("FrameIdentity", "sequence", 2**53, "unsafe JS integer"),
        ("FrameIdentity", "width", 8193, "oversized frame"),
        ("FrameIdentity", "source_timestamp_ms", 1.0, "invented producer clock"),
        ("FrameIdentity", "source_clock", "producer", "missing producer time"),
        ("FrameIdentity", "source_id", "/dev/video0", "arbitrary device path"),
        ("NeuralSample", "observation_u8", [0]*255, "short observation"),
        ("NeuralSample", "observation_u8", [256]*256, "pixel range"),
        ("NeuralSample", "observation_u8", [True]*256, "bool pixels"),
        ("NeuralSample", "completed_monotonic_ms", 99.0, "reversed response time"),
        ("NeuralSample", "motor_rates_hz.steer_L", -1.0, "negative motor rate"),
        ("FlightControls", "pixels", [0]*256, "decoder rejects pixels"),
        ("FlightControls", "goal", [0, 0], "decoder rejects target"),
        ("FlightControls", "expires_monotonic_ms", 199.0, "reversed expiry"),
        ("FlightControls", "expires_monotonic_ms", 2201.0, "overlong expiry"),
        ("FlightControls", "yaw_rate_rad_s", 4.0, "unbounded turn"),
        ("FlightSnapshot", "position", [0, 0], "wrong vector shape"),
        ("SyntheticFlightPreview", "dt_ms", 21, "preview variable step rejected"),
        ("SyntheticFlightPreview", "snapshots", [flight, {**flight, "tick": 2}], "preview tick gap"),
        ("SyntheticFlightPreview", "snapshots", [flight, {**flight, "tick": 1, "generation": 2}], "preview foreign epoch"),
        ("SyntheticFlightPreview", "snapshots", [flight, {**flight, "tick": 1, "evidence_kind": "real"}], "preview false real label"),
        ("SyntheticFlightPreview", "snapshots", [flight], "preview too short"),
        ("SessionConfig", "recording", "false", "coerced consent"),
        ("SessionConfig", "learning_enabled", 0, "numeric false literal"),
        ("EncoderConfig", "padding_u8", False, "boolean padding literal"),
        ("SessionConfig", "duration_seconds", 121, "session duration cap"),
        ("SessionConfig", "max_model_calls", 513, "session call cap"),
        ("SessionConfig", "source_id", "https://example.com", "URL source"),
        ("SessionConfig", "seed", -1, "negative seed"),
        ("StreamEnvelope", "flight.generation", 2, "foreign stream epoch"),
        ("StreamEnvelope", "neural_sample.frame.session_id", "other", "foreign stream session"),
        ("StreamEnvelope", "latest_source_frame.evidence_kind", "real", "mixed stream evidence"),
        ("StreamEnvelope", "latest_source_frame.source_id", "other", "source switch within generation"),
        ("ReplayManifest", "config.recording", False, "replay without consent"),
        ("ReplayManifest", "source.source_id", "other", "foreign replay source"),
        ("ReplayManifest", "events_file", "../secrets", "replay traversal"),
        ("ReplayManifest", "events_sha256", "invalid", "invalid event digest"),
        ("ReplayManifest", "initial_flight.tick", 1, "noninitial replay state"),
        ("ReplayManifest", "config.evidence_kind", "real", "mixed replay evidence"),
        ("ReplayManifest", "source.backend", "ffmpeg-v4l2", "nested source backend mismatch"),
        ("ReplayManifest", "events_bytes", 33554433, "oversized replay"),
        ("StartRequest", "recording_consent", True, "recording consent/config mismatch"),
        ("StartRequest", "owner_token", "short", "unprotected owner token"),
        ("OwnerRequest", "generation", 0, "invalid owner epoch"),
        ("PreviewRequest", "duration_seconds", 31, "preview duration bound"),
        ("ApiSnapshot", "last_inferred.frame.generation", 2, "foreign historical input"),
        ("ApiSnapshot", "last_inferred.frame.source_id", "other", "foreign historical source"),
        ("ApiSnapshot", "last_inferred.response_id", "other", "active historical response disagreement"),
        ("ApiSnapshot", "kind", "preview", "neural state in capture preview"),
        ("ApiSnapshot", "model_mode", "none", "neural session without model mode"),
        ("ApiSnapshot", "capture_hz", -1., "negative capture rate"),
        ("ServiceStatus", "current.flight.generation", 2, "foreign current snapshot"),
        ("SourceList", "sources.0.evidence_kind", "real", "mixed source list evidence"),
        ("SourcePreview", "rgb_base64", "", "preview pixel byte mismatch"),
        ("PreviewReply", "latest.frame.generation", 2, "foreign preview input"),
        ("FlightState", "snapshot.speed_units_s", 1., "flight velocity speed mismatch"),
    ]:
        bad(name, path, value, label)
    return cases
