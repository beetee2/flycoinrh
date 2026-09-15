"""Selected-device inspection. Only this bounded helper opens nodes for ioctls.

Linux generic ioctl ABI, checked for the supported x86_64/aarch64 Linux hosts.
No STREAMON, read, mmap, format-setting ioctl or automatic discovery probe.
"""
import ctypes
from dataclasses import asdict, dataclass
import fcntl
import json
import os
from pathlib import Path
import platform
import re
import stat
import struct
import sys

from .environment import metadata_command


class SourceError(ValueError):
    pass


def selected_path(source_id: str) -> Path:
    if not re.fullmatch(r"v4l2-video[0-9]{1,6}", source_id):
        raise SourceError("Select an explicit v4l2-videoN source ID from live-devices.")
    path = Path("/dev") / source_id.removeprefix("v4l2-")
    try:
        info = path.lstat()
        if path.resolve(strict=True) != path or not stat.S_ISCHR(info.st_mode) or os.major(info.st_rdev) != 81:
            raise SourceError("Selected source must be a resolved V4L2 character device, without symlinks.")
        if not os.access(path, os.R_OK | os.W_OK):
            raise SourceError("Selected source requires operator read/write permission.")
    except OSError:
        raise SourceError("Selected video device is unavailable; configure the OBS virtual camera.") from None
    return path


@dataclass(frozen=True)
class DeviceConfig:
    source_id: str
    device_number: int
    inode: int
    driver: str
    card: str
    capabilities: int
    width: int
    height: int
    fourcc: str
    bytes_per_line: int
    size_image: int
    field: int
    colorspace: int
    ycbcr_encoding: int
    quantization: int
    transfer: int
    fps_numerator: int
    fps_denominator: int
    formats: tuple[str, ...]
    extended_color: bool = True
    keep_format: int | None = None

    @property
    def producer_detection(self):
        # v4l2loopback exclusive capabilities reflect its writer stream token.
        # keep_format can keep CAPTURE advertised after stop, so it must be off.
        return "driver" if self.capabilities & 3 == 1 and self.keep_format == 0 else "unknown"

    @property
    def fps(self):
        return self.fps_denominator / self.fps_numerator

    @property
    def color_range(self):
        if self.fourcc in ("RGB3", "BGR3"):
            return "full"
        return "full" if self.quantization == 1 or (self.quantization == 0 and self.colorspace == 7) else "limited"

    def validate(self):
        if self.driver != "v4l2 loopback":
            raise SourceError("Selected driver is not v4l2loopback; webcams are not supported.")
        if self.capabilities & 0x04000001 != 0x04000001:
            raise SourceError("Selected OBS device must support single-plane capture and streaming; start OBS Virtual Camera.")
        if (type(self.width) is not int or type(self.height) is not int
                or not 1 <= self.width <= 8192 or not 1 <= self.height <= 8192
                or self.width * self.height * 3 > 32 * 1024 * 1024):
            raise SourceError("Capture dimensions exceed the 32 MiB RGB frame bound.")
        if self.fourcc not in ("RGB3", "BGR3", "YUYV", "NV12") or self.fourcc not in self.formats:
            raise SourceError("Select an uncompressed RGB24, BGR24, YUYV or NV12 OBS format.")
        if self.field != 1:
            raise SourceError("Only progressive frames are supported.")
        if not self.extended_color and (self.ycbcr_encoding, self.quantization, self.transfer) != (0, 0, 0):
            raise SourceError("Legacy driver color must use documented colorspace defaults.")
        if self.fps_numerator <= 0 or self.fps_denominator <= 0 or not 1 <= self.fps <= 60:
            raise SourceError("Select a declared rate between 1 and 60 fps.")
        row = self.width * {"RGB3": 3, "BGR3": 3, "YUYV": 2, "NV12": 1}[self.fourcc]
        size = row * self.height * (3 if self.fourcc == "NV12" else 2) // 2
        if self.bytes_per_line != row or self.size_image != size:
            raise SourceError("Padded or inconsistent input stride is unsupported; select tightly packed OBS output.")
        if self.fourcc in ("YUYV", "NV12"):
            if self.width % 2 or (self.fourcc == "NV12" and self.height % 2):
                raise SourceError("YUV dimensions must match chroma subsampling.")
            if (self.colorspace not in (1, 7, 8) or self.ycbcr_encoding not in (0, 1)
                    or self.quantization not in (0, 1, 2) or self.transfer not in (0, 1, 2)):
                raise SourceError("OBS v1 requires declared BT.601 SDR YUV color and range metadata.")
        elif self.quantization not in (0, 1) or self.colorspace not in (7, 8):
            raise SourceError("RGB input requires full-range sRGB metadata.")
        return self


class _FormatUnion(ctypes.Union):
    _fields_ = [("raw", ctypes.c_ubyte * 200), ("alignment", ctypes.c_void_p)]


class _Format(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint32), ("fmt", _FormatUnion)]


EXT_PIX_FORMAT = 0x00200000
PIX_FMT_PRIV_MAGIC = 0xFEEDCAFE


def _color_fields(caps, priv, encoding, quantization, transfer):
    if caps & EXT_PIX_FORMAT:
        if priv != PIX_FMT_PRIV_MAGIC:
            raise SourceError("Driver extended color metadata is invalid.")
        return encoding, quantization, transfer, True
    # Without extended-format support these bytes are undefined. Legacy color
    # is derived only from declared colorspace: SMPTE170M/JPEG/sRGB YUV or sRGB RGB.
    return 0, 0, 0, False


def _ioctl(fd, number, size, initial=b"", *, read_only=False):
    value = bytearray(size)
    value[:len(initial)] = initial
    request = ((2 if read_only else 3) << 30) | (size << 16) | (ord("V") << 8) | number
    fcntl.ioctl(fd, request, value, True)
    return value


def _inspect_selected(source_id: str) -> DeviceConfig:
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "aarch64"):
        raise SourceError("Selected-device inspector requires the Linux generic 64-bit ioctl ABI.")
    path = selected_path(source_id)
    before = path.stat()
    fd = os.open(path, os.O_RDWR | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        current = os.fstat(fd)
        if (current.st_rdev, current.st_ino) != (before.st_rdev, before.st_ino):
            raise SourceError("Selected device identity changed during opening.")
        cap = _ioctl(fd, 0, 104, read_only=True)
        driver, card, _, _, caps, device_caps = struct.unpack_from("16s32s32sIII", cap)
        if caps & 0x80000000:
            caps = device_caps
        initial = bytearray(ctypes.sizeof(_Format))
        struct.pack_into("I", initial, 0, 1)
        if caps & EXT_PIX_FORMAT:
            struct.pack_into("I", initial, _Format.fmt.offset + 28, PIX_FMT_PRIV_MAGIC)
        fmt = _ioctl(fd, 4, ctypes.sizeof(_Format), initial)
        width, height, fourcc, field, stride, size, color, priv, _, enc, quant, transfer = struct.unpack_from(
            "12I", fmt, _Format.fmt.offset)
        enc, quant, transfer, extended = _color_fields(caps, priv, enc, quant, transfer)
        keep_format = None
        if driver.split(b"\0")[0] == b"v4l2 loopback":
            try:
                control = _ioctl(fd, 27, 8, struct.pack("Ii", 0x0098F900, 0))
                keep_format = struct.unpack_from("i", control, 4)[0]
            except OSError as exc:
                if exc.errno != 22:
                    raise
        parm = _ioctl(fd, 21, 204, struct.pack("I", 1))
        numerator, denominator = struct.unpack_from("II", parm, 12)
        formats = []
        for index in range(128):
            try:
                desc = _ioctl(fd, 2, 64, struct.pack("II", index, 1))
            except OSError as exc:
                if exc.errno != 22:
                    raise
                break
            formats.append(bytes(desc[44:48]).decode("ascii"))
        else:
            raise SourceError("Device format enumeration exceeds its bound.")
        return DeviceConfig(source_id, current.st_rdev, current.st_ino,
                            driver.split(b"\0")[0].decode("ascii"), card.split(b"\0")[0].decode("ascii"),
                            caps, width, height, fourcc.to_bytes(4, sys.byteorder).decode("ascii"), stride, size,
                            field, color, enc, quant, transfer, numerator, denominator, tuple(formats), extended,
                            keep_format).validate()
    finally:
        os.close(fd)


def inspect_selected(source_id: str, *, timeout: float = 1.0) -> DeviceConfig:
    """Explicit selection is mandatory. Bound even a driver blocked in open/ioctl."""
    selected_path(source_id)
    report = metadata_command([sys.executable, "-m", "flytrap.live.device", source_id], timeout=timeout)
    if report["status"] != "ok":
        # Helper emits only fixed errors, never raw device/subprocess diagnostics.
        detail = report["output"].strip() if report["status"] == "failed" else report["status"]
        raise SourceError(f"Selected-device inspection failed: {detail[:256]}")
    try:
        config = json.loads(report["output"])
        config["formats"] = tuple(config["formats"])
        return DeviceConfig(**config).validate()
    except (TypeError, KeyError, ValueError):
        raise SourceError("Invalid selected-device inspection response.") from None


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise SourceError("An explicit source ID is required.")
        print(json.dumps(asdict(_inspect_selected(sys.argv[1]))))
    except SourceError as exc:
        print(str(exc))
        raise SystemExit(2) from None
    except (OSError, UnicodeError, ValueError):
        print("Selected device query failed; check OBS output and operator access.")
        raise SystemExit(2) from None
