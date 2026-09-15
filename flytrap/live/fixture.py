"""Explicitly labeled deterministic, original test imagery. No capture or model."""
from flytrap.live.contracts import FrameIdentity
from flytrap.live.encoding import RGBFrame

FIXTURE_SOURCE_ID = "fixture-pattern"
# 3 x 5 decimal glyphs keep the frame counter readable without font dependencies.
_DIGITS = ("111101101101111", "010110010010111", "111001111100111",
           "111001111001111", "101101111001001", "111100111001111",
           "111100111101111", "111001010010010", "111101111101111",
           "111101111001111")


def fixture_frame(sequence: int, session_id: str, generation: int, *,
                  width: int = 320, height: int = 180,
                  receipt_monotonic_ms: float | None = None) -> RGBFrame:
    """Render a sequence-indexed fixture. Default timing is deterministic at 30 Hz.

    Real-time producers pass their actual receipt clock. The source timestamp is
    a declared producer clock derived from sequence, never an OBS timestamp.
    """
    source_timestamp = sequence * 1000.0 / 30 if type(sequence) is int else 0.0
    identity = FrameIdentity(schema_version="obs-frame-1", source_id=FIXTURE_SOURCE_ID,
                             session_id=session_id, generation=generation, sequence=sequence,
                             evidence_kind="fixture", width=width, height=height,
                             pixel_format="RGB24", receipt_monotonic_ms=(source_timestamp
                                 if receipt_monotonic_ms is None else receipt_monotonic_ms),
                             source_timestamp_ms=source_timestamp, source_sequence=sequence,
                             source_clock="producer")
    # A deliberate fixture-specific cap prevents accidental giant Python renders.
    if width * height > 1920 * 1080:
        raise ValueError("fixture pattern is bounded to 1920 x 1080 pixels")
    output = bytearray(bytes((18, 24, 38)) * (width * height))

    def rectangle(x0, y0, x1, y1, color):
        start, end = max(0, x0), min(width, x1)
        if start >= end:
            return
        row = bytes(color) * (end - start)
        for y in range(max(0, y0), min(height, y1)):
            offset = (y * width + start) * 3
            output[offset:offset + len(row)] = row

    # Fixed red/green/blue orientation markers and moving gold/cyan rectangles.
    marker = max(1, min(width, height) // 10)
    rectangle(0, 0, marker, marker, (255, 0, 0))
    rectangle(width - marker, 0, width, marker, (0, 255, 0))
    rectangle(0, height - marker, marker, height, (0, 0, 255))
    size = max(1, min(width, height) // 5)
    moving_x = sequence * 7 % max(1, width - size + 1)
    moving_y = sequence * 3 % max(1, height - size + 1)
    rectangle(moving_x, height // 3, moving_x + size, height // 3 + size, (255, 192, 32))
    rectangle(width // 2, moving_y, width // 2 + size, moving_y + size, (24, 220, 240))
    scale = max(1, min(width // 80, height // 20))
    for digit_index, digit in enumerate(str(sequence)):
        for pixel, enabled in enumerate(_DIGITS[int(digit)]):
            if enabled == "1":
                x = marker + digit_index * 4 * scale + pixel % 3 * scale
                y = height - 6 * scale + pixel // 3 * scale
                rectangle(x, y, x + scale, y + scale, (255, 255, 255))
    return RGBFrame(identity, bytes(output))
