"""Synthetic V4L2 metadata/ioctl fixtures; no host capture device is opened."""
from dataclasses import asdict, replace
import json
from pathlib import Path
import stat
import struct
import time
from types import SimpleNamespace

import pytest

from flytrap.live import device
from flytrap.live.device import DeviceConfig, SourceError


def configuration(**changes):
    config = DeviceConfig("v4l2-video7", 20743, 1234, "v4l2 loopback", "OBS fixture",
                          0x04200001, 640, 480, "YUYV", 1280, 614400, 1, 1, 1, 2, 1,
                          1, 30, ("YUYV", "RGB3", "BGR3", "NV12"))
    return replace(config, **changes)


@pytest.mark.parametrize("changes", [
    {"driver": "uvcvideo"}, {"capabilities": 1}, {"capabilities": 0x04000000},
    {"width": 0}, {"width": True}, {"height": 8193}, {"width": 8192, "height": 8192},
    {"fourcc": "MJPG"}, {"formats": ("RGB3",)}, {"field": 4},
    {"fps_numerator": 0}, {"fps_denominator": 61}, {"fps_numerator": 31},
    {"bytes_per_line": 1281}, {"size_image": 614401},
    {"colorspace": 3}, {"ycbcr_encoding": 2}, {"quantization": 3}, {"transfer": 7},
])
def test_device_rejects_unsupported_or_ambiguous_capture_metadata(changes):
    with pytest.raises(SourceError):
        configuration(**changes).validate()


@pytest.mark.parametrize("changes,expected_range", [
    ({}, "limited"), ({"quantization": 1}, "full"),
    ({"colorspace": 7, "quantization": 0}, "full"),
    ({"colorspace": 8, "ycbcr_encoding": 0, "quantization": 0, "transfer": 0}, "limited"),
    ({"fourcc": "NV12", "bytes_per_line": 640, "size_image": 460800}, "limited"),
    ({"fourcc": "RGB3", "bytes_per_line": 1920, "size_image": 921600,
      "colorspace": 8, "quantization": 0}, "full"),
    ({"fourcc": "BGR3", "bytes_per_line": 1920, "size_image": 921600,
      "colorspace": 8, "quantization": 1}, "full"),
])
def test_supported_formats_have_declared_range_and_rate(changes, expected_range):
    config = configuration(**changes).validate()
    assert config.color_range == expected_range
    assert config.fps == 30


@pytest.mark.parametrize("changes", [
    {"width": 639, "bytes_per_line": 1278, "size_image": 613440},
    {"fourcc": "NV12", "height": 479, "bytes_per_line": 640, "size_image": 459840},
    {"fourcc": "RGB3", "bytes_per_line": 1920, "size_image": 921600,
     "colorspace": 8, "quantization": 2},
])
def test_chroma_subsampling_and_rgb_range_are_checked(changes):
    with pytest.raises(SourceError):
        configuration(**changes).validate()


@pytest.mark.parametrize("source", ["/dev/video0", "https://example.invalid", "v4l2-video7;sh",
                                    "v4l2-video../1", "fixture-pattern", "v4l2-video9999999", ""])
def test_arbitrary_sources_rejected_before_stat_or_open(source, monkeypatch):
    monkeypatch.setattr(Path, "lstat", lambda _: pytest.fail("invalid source reached filesystem"))
    monkeypatch.setattr(device.os, "open", lambda *a, **k: pytest.fail("device opened"))
    with pytest.raises(SourceError):
        device.selected_path(source)


@pytest.mark.parametrize("kind", ["regular", "wrong_major", "symlink", "permission", "missing"])
def test_selected_path_requires_resolved_v4l2_character_device_and_permissions(kind, monkeypatch):
    info = SimpleNamespace(st_mode=stat.S_IFCHR, st_rdev=device.os.makedev(81, 7))
    if kind == "regular":
        info.st_mode = stat.S_IFREG
    if kind == "wrong_major":
        info.st_rdev = device.os.makedev(1, 3)

    def lstat(_):
        if kind == "missing":
            raise FileNotFoundError
        return info

    monkeypatch.setattr(Path, "lstat", lstat)
    monkeypatch.setattr(Path, "resolve", lambda self, **_: Path("/dev/video8") if kind == "symlink" else self)
    monkeypatch.setattr(device.os, "access", lambda *a: kind != "permission")
    monkeypatch.setattr(device.os, "open", lambda *a, **k: pytest.fail("path inspection opened device"))
    with pytest.raises(SourceError):
        device.selected_path("v4l2-video7")


@pytest.mark.parametrize("keep_format", [0, 1, None])
def test_ioctl_layout_decodes_selected_metadata_without_streaming(monkeypatch, keep_format):
    metadata = SimpleNamespace(st_rdev=20743, st_ino=1234)
    monkeypatch.setattr(device.platform, "system", lambda: "Linux")
    monkeypatch.setattr(device.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(device, "selected_path", lambda _: Path("/not-a-device/fixture"))
    monkeypatch.setattr(Path, "stat", lambda _: metadata)
    opened, closed, ioctls = [], [], []
    monkeypatch.setattr(device.os, "open", lambda path, flags: opened.append((path, flags)) or 77)
    monkeypatch.setattr(device.os, "fstat", lambda fd: metadata)
    monkeypatch.setattr(device.os, "close", closed.append)

    def ioctl(fd, request, value, mutate):
        assert fd == 77 and mutate is True
        number = request & 255
        ioctls.append(number)
        if number == 0:
            struct.pack_into("16s32s32sIII", value, 0, b"v4l2 loopback", b"OBS fixture", b"fixture",
                             1, 0x80000000, 0x04200001)
        elif number == 4:
            assert struct.unpack_from("I", value)[0] == 1
            assert struct.unpack_from("I", value, device._Format.fmt.offset + 28)[0] == device.PIX_FMT_PRIV_MAGIC
            struct.pack_into("12I", value, device._Format.fmt.offset,
                             640, 480, int.from_bytes(b"YUYV", "little"), 1, 1280, 614400, 1,
                             device.PIX_FMT_PRIV_MAGIC, 0, 1, 2, 1)
        elif number == 21:
            struct.pack_into("II", value, 12, 1, 30)
        elif number == 27:
            assert struct.unpack_from("I", value)[0] == 0x0098F900
            if keep_format is None:
                raise OSError(22, "keep_format unavailable in fixture")
            struct.pack_into("i", value, 4, keep_format)
        elif number == 2:
            if struct.unpack_from("I", value)[0] > 0:
                raise OSError(22, "end fixture formats")
            value[44:48] = b"YUYV"
        else:
            pytest.fail("unexpected ioctl (capture/format mutation forbidden)")

    monkeypatch.setattr(device.fcntl, "ioctl", ioctl)
    config = device._inspect_selected("v4l2-video7")
    assert config == configuration(formats=("YUYV",), keep_format=keep_format)
    assert config.producer_detection == ("driver" if keep_format == 0 else "unknown")
    assert ioctls == [0, 4, 27, 21, 2, 2]
    assert len(opened) == 1 and closed == [77]
    assert opened[0][1] & device.os.O_NONBLOCK and opened[0][1] & device.os.O_NOFOLLOW


def test_identity_swap_closes_descriptor_before_any_ioctl(monkeypatch):
    monkeypatch.setattr(device, "selected_path", lambda _: Path("/not-a-device/fixture"))
    monkeypatch.setattr(Path, "stat", lambda _: SimpleNamespace(st_rdev=20743, st_ino=1234))
    monkeypatch.setattr(device.os, "open", lambda *a, **k: 77)
    monkeypatch.setattr(device.os, "fstat", lambda _: SimpleNamespace(st_rdev=20744, st_ino=1234))
    closed = []
    monkeypatch.setattr(device.os, "close", closed.append)
    monkeypatch.setattr(device.fcntl, "ioctl", lambda *a: pytest.fail("identity swap reached ioctl"))
    with pytest.raises(SourceError, match="identity changed"):
        device._inspect_selected("v4l2-video7")
    assert closed == [77]


@pytest.mark.parametrize("status", ["timeout", "missing", "output_limit", "unavailable"])
def test_inspection_delegates_explicit_source_and_deadline_then_fails_closed(status, monkeypatch):
    monkeypatch.setattr(device, "selected_path", lambda _: Path("/not-a-device/fixture"))
    calls = []

    def metadata(arguments, **kwargs):
        calls.append((arguments, kwargs))
        return {"status": status, "output": "", "exit_code": -9}

    monkeypatch.setattr(device, "metadata_command", metadata)
    with pytest.raises(SourceError, match=status):
        device.inspect_selected("v4l2-video7", timeout=.25)
    arguments, kwargs = calls[0]
    assert arguments == [device.sys.executable, "-m", "flytrap.live.device", "v4l2-video7"]
    assert kwargs == {"timeout": .25}


def test_subprocess_response_is_revalidated(monkeypatch):
    monkeypatch.setattr(device, "selected_path", lambda _: Path("/not-a-device/fixture"))
    result = {"status": "ok", "output": json.dumps(asdict(configuration()))}
    monkeypatch.setattr(device, "metadata_command", lambda *a, **k: result)
    assert device.inspect_selected("v4l2-video7") == configuration()
    result["output"] = json.dumps(asdict(configuration(driver="uvcvideo")))
    with pytest.raises(SourceError):
        device.inspect_selected("v4l2-video7")
    result["output"] = "[]"
    with pytest.raises(SourceError):
        device.inspect_selected("v4l2-video7")


def test_actual_hung_metadata_helper_is_terminated_within_deadline(monkeypatch):
    from flytrap.live.environment import metadata_command

    monkeypatch.setattr(device, "selected_path", lambda _: Path("/not-a-device/fixture"))
    reports = []

    def stalled_helper(arguments, **kwargs):
        # Actual subprocess lifecycle, synthetic program: no source node opened.
        report = metadata_command([device.sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)
        reports.append(report)
        return report

    monkeypatch.setattr(device, "metadata_command", stalled_helper)
    started = time.monotonic()
    with pytest.raises(SourceError, match="timeout"):
        device.inspect_selected("v4l2-video7", timeout=.08)
    assert time.monotonic() - started < .75
    assert reports[0]["exit_code"] is not None


def test_undefined_extended_color_bytes_never_override_legacy_defaults():
    assert device._color_fields(0x04000001, 0, 99, 1, 99) == (0, 0, 0, False)
    legacy = configuration(extended_color=False, ycbcr_encoding=0, quantization=0, transfer=0)
    assert legacy.validate().color_range == "limited"
    with pytest.raises(SourceError, match="Legacy"):
        configuration(extended_color=False).validate()


def test_extended_color_requires_driver_magic():
    with pytest.raises(SourceError, match="extended color"):
        device._color_fields(device.EXT_PIX_FORMAT, 0, 1, 1, 1)
    assert device._color_fields(device.EXT_PIX_FORMAT, device.PIX_FMT_PRIV_MAGIC, 1, 2, 1) == (1, 2, 1, True)


@pytest.mark.parametrize("capabilities,keep_format,expected", [
    (0x04200001, 0, "driver"),
    (0x04000001, 0, "driver"),
    (0x04200003, 0, "unknown"),
    (0x04200001, 1, "unknown"),
    (0x04200001, None, "unknown"),
    (0x04200001, -1, "unknown"),
    (0x04200001, 2, "unknown"),
])
def test_driver_status_requires_exclusive_capture_and_unlocked_format(capabilities, keep_format, expected):
    descriptor = configuration(capabilities=capabilities, keep_format=keep_format).validate()
    assert descriptor.producer_detection == expected


def test_output_only_stopped_producer_is_not_valid_capture():
    descriptor = configuration(capabilities=0x04200002, keep_format=0)
    assert descriptor.producer_detection == "unknown"
    with pytest.raises(SourceError, match="start OBS"):
        descriptor.validate()
