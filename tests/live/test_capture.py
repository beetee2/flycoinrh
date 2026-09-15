"""Hardware-free capture boundary probes, including actual FFmpeg buffering."""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from flytrap.live import capture as module
from flytrap.live.capture import Capture, LatestFrameSlot, PPMReader, output_arguments
from flytrap.live.device import DeviceConfig, SourceError
from flytrap.live.encoding import RGBFrame
from flytrap.live.fixture import fixture_frame
from flytrap.live.producer import ProducerStatus


def config(width=64, height=32):
    return DeviceConfig("v4l2-video9", 81, 1, "v4l2 loopback", "Synthetic test device metadata",
                        0x04000001, width, height, "RGB3", width * 3, width * height * 3,
                        1, 8, 0, 1, 0, 1, 30, ("RGB3",))


def wait_for(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < deadline, "bounded condition did not occur"
        time.sleep(.005)


def fake_backend(monkeypatch, arguments, *, device=None, **kwargs):
    # This replaces only selection and arguments. Actual subprocess/pipe/reader
    # lifecycle is exercised using a synthetic executable or FFmpeg source.
    monkeypatch.setattr(module, "inspect_selected", lambda *a, **k: device or config())
    monkeypatch.setattr(module, "ffmpeg_arguments", lambda _: arguments)
    return Capture(source_id="v4l2-video9", session_id="fixture-backend", generation=1, **kwargs)


def child(script):
    return [sys.executable, "-u", "-c", script]


def test_slot_rejects_old_foreign_epochs_sequences_and_time():
    slot = LatestFrameSlot("fixture-pattern", "session-a", 2)
    frame = fixture_frame(10, "session-a", 2, receipt_monotonic_ms=100.)
    assert slot.put(frame)
    for changes in ({"generation": 1}, {"session_id": "session-b"}, {"source_id": "other"},
                    {"sequence": 9}, {"receipt_monotonic_ms": 99., "sequence": 11}):
        bad = RGBFrame(frame.identity.model_copy(update=changes), frame.rgb)
        assert not slot.put(bad)
    assert slot.take() == frame
    assert slot.rejected == 5
    slot.close()
    assert slot.latest() is None
    assert not slot.put(fixture_frame(12, "session-a", 2))


def test_slot_counts_only_unconsumed_overwrites_and_wakes_on_close():
    slot = LatestFrameSlot("fixture-pattern", "fixture-session", 1)
    for index in range(4):
        slot.put(fixture_frame(index, "fixture-session", 1))
    assert slot.overwritten == 3 and slot.accepted == 4
    assert slot.take().identity.sequence == 3
    result = []
    worker = threading.Thread(target=lambda: result.append(slot.take(2)))
    worker.start()
    slot.close()
    worker.join(.5)
    assert not worker.is_alive() and result == [None]


def test_preview_retains_only_newest_frame_independently_of_inference_consumption():
    slot = LatestFrameSlot("fixture-pattern", "fixture-session", 1)
    first = fixture_frame(0, "fixture-session", 1)
    second = fixture_frame(1, "fixture-session", 1)
    assert slot.put(first)
    assert slot.take() == first and slot.latest() is None
    assert slot.latest_preview() == first
    assert slot.put(second)
    assert slot.latest_preview() == second
    assert slot.overwritten == 0 and slot.accepted == 2
    assert slot.take() == second
    slot.close()
    assert slot.latest_preview() is None


def test_same_pixels_new_timing_is_admitted():
    slot = LatestFrameSlot("fixture-pattern", "fixture-session", 1)
    frame = fixture_frame(0, "fixture-session", 1)
    assert slot.put(frame)
    newer = RGBFrame(frame.identity.model_copy(update={"sequence": 1,
                     "receipt_monotonic_ms": frame.identity.receipt_monotonic_ms + 50}), frame.rgb)
    assert slot.put(newer)
    assert slot.take() == newer


def test_partial_parser_preserves_channels_orientation_and_multiple_frames():
    rgb = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 1, 2, 3])
    payload = (b"P6\n2 2\n255\n" + rgb) * 3
    for step in (1, 2, 7, 100):
        parser, frames = PPMReader(2, 2), []
        for offset in range(0, len(payload), step):
            frames.extend(parser.feed(payload[offset:offset + step]))
        parser.eof()
        assert frames == [rgb] * 3


@pytest.mark.parametrize("payload", [b"P6\n3 2\n255\n", b"P5\n2 2\n255\n", b"x" * 65,
                                   b"P6\n2 2\n65535\n"])
def test_parser_rejects_format_changes_and_malformed_headers(payload):
    with pytest.raises(SourceError):
        PPMReader(2, 2).feed(payload)


@pytest.mark.parametrize("payload", [b"P6", b"P6\n2 2\n255\n", b"P6\n2 2\n255\n123"])
def test_parser_reports_partial_eof(payload):
    reader = PPMReader(2, 2)
    reader.feed(payload)
    with pytest.raises(SourceError, match="partial"):
        reader.eof()


def test_parser_rejects_oversized_allocations():
    with pytest.raises(SourceError):
        PPMReader(8192, 8192)
    with pytest.raises(SourceError):
        PPMReader(2, 2).feed(b"x" * 65537)


@pytest.mark.parametrize("script,reason", [
    ("import time; time.sleep(10)", "receipt deadline"),
    ("import sys; sys.stdout.buffer.write(b'P6\\n64 32\\n255\\n123'); sys.stdout.flush()", "partial"),
    ("pass", "EOF"),
    ("import sys; sys.stdout.buffer.write(b'P6\\n32 64\\n255\\n'); sys.stdout.flush()", "format changed"),
])
def test_backend_hangs_partial_eof_and_format_changes_are_bounded(monkeypatch, script, reason):
    capture = fake_backend(monkeypatch, child(script), inactivity_s=.2).start()
    wait_for(lambda: capture.status().state == "source_lost")
    capture.stop()
    assert reason in capture.status().reason
    assert capture._child.poll() is not None
    assert not capture._thread.is_alive() and not capture._watcher.is_alive()
    assert capture.slot.latest() is None


def test_stderr_flood_does_not_block_capture_and_diagnostics_are_bounded(monkeypatch):
    script = ("import sys,time; sys.stderr.write('secret-with-control\\x1b' * 100000); sys.stderr.flush(); "
              "sys.stdout.buffer.write(b'P6\\n64 32\\n255\\n'+bytes(64*32*3)); sys.stdout.flush(); time.sleep(10)")
    capture = fake_backend(monkeypatch, child(script)).start()
    try:
        wait_for(lambda: capture.slot.accepted > 0)
        assert len(capture._diagnostics) <= 4096
        assert b"\x1b" not in capture._diagnostics
        assert "secret" not in repr(capture.status())
    finally:
        capture.stop()
    assert capture._child.poll() is not None


def test_stop_kills_and_reaps_uncooperative_child(monkeypatch):
    script = ("import signal,sys,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
              "sys.stdout.buffer.write(b'P6\\n64 32\\n255\\n'+bytes(64*32*3)); sys.stdout.flush(); time.sleep(10)")
    capture = fake_backend(monkeypatch, child(script)).start()
    wait_for(lambda: capture.slot.accepted > 0)
    start = time.monotonic()
    assert capture.stop().state == "stopped"
    assert time.monotonic() - start < 3
    assert capture._child.poll() == -9
    assert capture.stop().state == "stopped"


def test_stop_during_open_inspection_does_not_launch_capture(monkeypatch):
    entered, release = threading.Event(), threading.Event()

    def inspect(*args, **kwargs):
        entered.set()
        assert release.wait(1)
        return config()

    monkeypatch.setattr(module, "inspect_selected", inspect)
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: pytest.fail("capture after stop"))
    capture = Capture(source_id="v4l2-video9", session_id="fixture-race", generation=1)
    starter = threading.Thread(target=capture.start)
    starter.start()
    assert entered.wait(1)
    stopper = threading.Thread(target=capture.stop)
    stopper.start()
    assert capture._stop.wait(1)
    release.set()
    starter.join(1)
    stopper.join(1)
    assert capture.status().state == "stopped"
    assert capture._child is None


def test_metadata_format_change_stops_same_size_stream(monkeypatch):
    script = "import sys,time\nwhile True:\n sys.stdout.buffer.write(b'P6\\n64 32\\n255\\n'+bytes(64*32*3)); sys.stdout.flush(); time.sleep(.03)"
    capture = fake_backend(monkeypatch, child(script)).start()
    wait_for(lambda: capture.slot.accepted > 0)
    monkeypatch.setattr(module, "inspect_selected", lambda *a, **k: replace(config(), quantization=2))
    wait_for(lambda: capture.status().state == "source_lost")
    capture.stop()
    assert "format changed" in capture.status().reason


class Monitor:
    state = "active"

    def snapshot(self):
        return ProducerStatus(self.state, time.monotonic() * 1000)

    def poll(self):
        return self.snapshot()


@pytest.mark.parametrize("state", ["inactive", "unknown"])
def test_repeated_static_frames_cannot_hide_producer_loss(monkeypatch, state):
    script = "import sys,time\nwhile True:\n sys.stdout.buffer.write(b'P6\\n64 32\\n255\\n'+bytes(64*32*3)); sys.stdout.flush(); time.sleep(.03)"
    monitor = Monitor()
    capture = fake_backend(monkeypatch, child(script), monitor=monitor, verified=True).start()
    try:
        wait_for(lambda: capture.slot.accepted >= 4)
        assert capture.status().verified_live
        assert capture.status().content_unchanged_ms >= 60
        monitor.state = state
        assert not capture.status().verified_live
        wait_for(lambda: capture.status().state == "source_lost")
    finally:
        capture.stop()


def test_unsupported_status_allows_only_unverified_preview(monkeypatch):
    script = "import sys,time\nwhile True:\n sys.stdout.buffer.write(b'P6\\n64 32\\n255\\n'+bytes(64*32*3)); sys.stdout.flush(); time.sleep(.03)"
    capture = fake_backend(monkeypatch, child(script)).start()
    try:
        wait_for(lambda: capture.slot.accepted >= 4)
        assert not capture.status().verified_live
        assert capture.status().producer == "unknown"
    finally:
        capture.stop()
    with pytest.raises(SourceError, match="monitor"):
        Capture(source_id="v4l2-video9", session_id="fixture-session", generation=1, verified=True).start()


@pytest.mark.parametrize("descriptor", [
    replace(config(), keep_format=None),
    replace(config(), keep_format=1),
    replace(config(), keep_format=0, capabilities=0x04000003),
])
def test_verified_start_rejects_unreliable_driver_before_ffmpeg(monkeypatch, descriptor):
    monkeypatch.setattr(module, "inspect_selected", lambda *a, **k: descriptor)
    monkeypatch.setattr(module, "ffmpeg_arguments", lambda *a: pytest.fail("unreliable source reached backend"))
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: pytest.fail("unreliable source opened capture"))
    capture = Capture(source_id="v4l2-video9", session_id="fixture-unreliable-driver", generation=1,
                      verified=True)
    with pytest.raises(SourceError, match="reliable driver status"):
        capture.start()
    assert capture._child is None and capture.slot.accepted == 0
    assert capture.status().state == "failed"
    assert not capture.status().verified_live


@pytest.mark.parametrize("keep_format", [1, None])
def test_keep_format_change_stops_verified_capture_and_reaps(monkeypatch, keep_format):
    descriptor = replace(config(), keep_format=0)
    script = "import sys,time\nwhile True:\n sys.stdout.buffer.write(b'P6\\n64 32\\n255\\n'+bytes(64*32*3)); sys.stdout.flush(); time.sleep(.03)"
    capture = fake_backend(monkeypatch, child(script), device=descriptor, verified=True).start()
    try:
        wait_for(lambda: capture.slot.accepted >= 4)
        assert capture.status().verified_live
        assert capture.status().producer == "active"
        monkeypatch.setattr(module, "inspect_selected", lambda *a, **k: replace(descriptor, keep_format=keep_format))
        wait_for(lambda: capture.status().state == "source_lost")
        assert not capture.status().verified_live
        assert capture.slot.latest() is None
    finally:
        capture.stop()
    assert capture._child.poll() is not None
    assert not capture._watcher.is_alive() and not capture._thread.is_alive()


def test_driver_heartbeat_is_renewed_by_inspection_with_static_source(monkeypatch):
    descriptor = replace(config(), keep_format=0)
    script = "import sys,time\nwhile True:\n sys.stdout.buffer.write(b'P6\\n64 32\\n255\\n'+bytes(64*32*3)); sys.stdout.flush(); time.sleep(.03)"
    capture = fake_backend(monkeypatch, child(script), device=descriptor, verified=True, inactivity_s=.75).start()
    try:
        wait_for(lambda: capture.slot.accepted >= 4)
        initial_check = capture._producer_checked
        wait_for(lambda: capture._producer_checked >= initial_check + .8)
        status = capture.status()
        assert status.producer == "active" and status.verified_live
        assert status.content_unchanged_ms >= 750
    finally:
        capture.stop()


def test_new_static_frames_do_not_renew_expired_driver_heartbeat(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(module, "time", SimpleNamespace(monotonic=lambda: now[0]))
    capture = Capture(source_id="v4l2-video9", session_id="fixture-expired-driver", generation=1,
                      verified=True, inactivity_s=.5)
    capture._started = 100.
    capture._state = "previewing"
    capture._producer = "active"
    capture._producer_checked = 100.
    capture._accept(bytes(64 * 32 * 3), 64, 32)
    assert capture.status().verified_live
    now[0] = 100.5
    capture._accept(bytes(64 * 32 * 3), 64, 32)
    status = capture.status()
    assert status.accepted_frames == 2
    assert status.producer == "unknown"
    assert not status.verified_live
    assert status.content_unchanged_ms == 500


def test_explicit_fixture_capture_expires_without_any_device_or_model(monkeypatch):
    monkeypatch.setattr(module, "inspect_selected", lambda *a, **k: pytest.fail("fixture inspected device"))
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: pytest.fail("fixture spawned process"))
    capture = Capture(source_id="fixture-pattern", session_id="fixture-session", generation=1, duration_s=.2)
    assert capture.status().state == "idle" and capture.slot.accepted == 0
    capture.start()
    wait_for(lambda: capture.status().state == "limit_reached")
    assert capture.slot.accepted >= 2
    assert capture.slot.latest() is None
    capture.stop()
    with pytest.raises(SourceError, match="single-use"):
        capture.start()


def test_actual_ffmpeg_visible_indices_stay_recent_for_slow_consumer(monkeypatch, tmp_path):
    # Lavfi produces actual indexed pixels; normal FFmpeg encoder/pipe and the
    # production continuous reader are used. This is explicitly NOT V4L2 proof.
    arguments = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-re", "-f", "lavfi",
                 "-i", "nullsrc=s=64x32:r=30,geq=r='N':g='0':b='0'", *output_arguments()]
    capture = fake_backend(monkeypatch, arguments, duration_s=5).start()
    samples = []
    try:
        wait_for(lambda: capture.slot.accepted >= 3)
        baseline = time.monotonic()
        first = capture.slot.take(1)
        initial_sequence = first.identity.sequence
        for delay in (.3, .4, .5):
            time.sleep(delay)  # Deliberately slow inference consumer; capture keeps draining.
            frame = capture.slot.take(1)
            assert frame is not None
            elapsed = time.monotonic() - baseline
            assert frame.identity.sequence - initial_sequence >= int(elapsed * 30) - 3
            assert frame.rgb[0] == frame.identity.sequence
            assert time.monotonic() * 1000 - frame.identity.receipt_monotonic_ms < 150
            assert frame.identity.source_sequence is None  # No fabricated producer metadata.
            samples.append({"elapsed_s": elapsed, "sequence": frame.identity.sequence,
                            "visible_pixel_index": frame.rgb[0]})
        assert capture.slot.overwritten >= 25
        evidence = {"kind": "fixture-actual-ffmpeg", "samples": samples,
                    "overwritten": capture.slot.overwritten, "v4l2_gate": "deferred"}
        (tmp_path / "buffering.json").write_text(json.dumps(evidence))
        print(json.dumps(evidence))
    finally:
        capture.stop()
    assert capture._child.poll() is not None


@pytest.mark.parametrize("pixel_format,rgb", [("rgb24", bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255])),
                                            ("bgr24", bytes([0, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255, 255]))])
def test_actual_ffmpeg_channel_order_and_orientation(tmp_path, pixel_format, rgb):
    raw = tmp_path / "fixture.rgb"
    raw.write_bytes(rgb)
    result = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-f", "rawvideo",
                             "-pixel_format", pixel_format, "-video_size", "2x2", "-i", str(raw),
                             *output_arguments()], capture_output=True, timeout=3)
    assert result.returncode == 0, result.stderr
    parser = PPMReader(2, 2)
    frames = parser.feed(result.stdout)
    parser.eof()
    assert frames == [bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255])]


def test_no_neural_dependencies_in_capture_layers():
    for name in ("capture", "encoding", "device", "fixture", "producer", "preview"):
        source = Path(module.__file__).with_name(name + ".py").read_text()
        assert "import flysim" not in source
        assert "controllers.fly" not in source


def test_confirmed_identity_change_rejected_before_capture(monkeypatch):
    monkeypatch.setattr(module, "inspect_selected", lambda *a, **k: replace(config(), card="Other virtual camera"))
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: pytest.fail("opened changed device"))
    capture = Capture(source_id="v4l2-video9", session_id="fixture-selection", generation=1,
                      expected_device=config())
    with pytest.raises(SourceError, match="operator-confirmed"):
        capture.start()
    assert capture.status().state == "failed" and capture._child is None


@pytest.mark.parametrize("format_name,source_range,raw,expected", [
    ("yuyv422", "limited", bytes([16, 128, 235, 128, 81, 90, 81, 240]),
     bytes([0, 0, 0, 255, 255, 255, 255, 0, 0, 255, 0, 0])),
    ("yuyv422", "full", bytes([0, 128, 255, 128, 76, 85, 76, 255]),
     bytes([0, 0, 0, 255, 255, 255, 254, 0, 0, 254, 0, 0])),
    ("nv12", "limited", bytes([81, 81, 81, 81, 90, 240]), bytes([255, 0, 0] * 4)),
])
def test_actual_ffmpeg_bt601_range_conversion(tmp_path, format_name, source_range, raw, expected):
    fixture = tmp_path / "fixture.yuv"
    fixture.write_bytes(raw)
    result = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-f", "rawvideo",
                             "-pixel_format", format_name, "-video_size", "2x2", "-i", str(fixture),
                             "-vf", f"scale=iw:ih:in_color_matrix=bt601:in_range={source_range}:out_range=full",
                             *output_arguments()], capture_output=True, timeout=3)
    assert result.returncode == 0, result.stderr
    frame, = PPMReader(2, 2).feed(result.stdout)
    assert all(abs(actual - target) <= 3 for actual, target in zip(frame, expected, strict=True))
