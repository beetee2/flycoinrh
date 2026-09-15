"""Golden RGB/letterbox boundaries and generated independent decimal oracle."""
from dataclasses import FrozenInstanceError
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import math

from hypothesis import given, settings, strategies as st
import pytest

from flytrap.live.contracts import FrameIdentity
from flytrap.live.encoding import PreviewPair, RGBFrame, encode_frame, preview_pair
from flytrap.live.fixture import fixture_frame


def frame(width, height, rgb, **overrides):
    values = dict(schema_version="obs-frame-1", source_id="fixture-pattern", session_id="test-session",
                  generation=1, sequence=0, evidence_kind="fixture", width=width, height=height,
                  pixel_format="RGB24", receipt_monotonic_ms=0.0, source_timestamp_ms=None,
                  source_sequence=None, source_clock="unknown")
    values.update(overrides)
    return RGBFrame(FrameIdentity(**values), rgb)


def reference(width, height, rgb):
    """Decimal sizing and list raster deliberately differ from production indexing."""
    scale = min(Decimal(16) / Decimal(width), Decimal(16) / Decimal(height))
    w, h = [max(1, int((Decimal(value) * scale).quantize(Decimal(1), rounding=ROUND_HALF_UP)))
            for value in (width, height)]
    raster = [[tuple(rgb[(y * width + x) * 3:(y * width + x + 1) * 3])
               for x in range(width)] for y in range(height)]
    output = [[0] * 16 for _ in range(16)]
    for y in range(h):
        for x in range(w):
            sx = min(width - 1, int((Decimal(x) + Decimal("0.5")) * width / w))
            sy = min(height - 1, int((Decimal(y) + Decimal("0.5")) * height / h))
            r, g, b = raster[sy][sx]
            output[(16 - h) // 2 + y][(16 - w) // 2 + x] = math.floor(
                Decimal(77 * r + 150 * g + 29 * b + 128) / Decimal(256))
    return bytes(value for row in output for value in row)


@pytest.mark.parametrize("rgb,gray", [((255, 0, 0), 77), ((0, 255, 0), 149),
                                     ((0, 0, 255), 29), ((255, 255, 255), 255),
                                     ((0, 0, 0), 0), ((0, 0, 128), 15)])
def test_solid_color_golden(rgb, gray):
    result = encode_frame(frame(1, 1, bytes(rgb)))
    assert result.u8 == bytes([gray]) * 256
    assert result.sha256 == sha256(bytes([gray]) * 256).hexdigest()
    assert result.observation.pixels == [gray / 255] * 256
    assert set(result.observation.model_dump()) == {"schema_version", "pixels"}


def test_quadrant_golden_pins_channel_order_top_down_and_no_mirroring():
    original = frame(2, 2, bytes((255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255)))
    result = encode_frame(original)
    expected = (bytes([77] * 8 + [149] * 8) * 8 + bytes([29] * 8 + [255] * 8) * 8)
    assert result.u8 == expected
    assert result.frame == original.identity
    assert result.sha256 == sha256(expected).hexdigest()


def test_half_up_dimensions_extra_padding_on_bottom():
    result = encode_frame(frame(32, 5, bytes((255, 255, 255)) * 160))
    assert result.u8 == bytes(16 * 6) + bytes([255]) * (16 * 3) + bytes(16 * 7)


def test_half_up_dimensions_extra_padding_on_right():
    result = encode_frame(frame(5, 32, bytes((255, 255, 255)) * 160))
    assert result.u8 == (bytes(6) + bytes([255]) * 3 + bytes(7)) * 16


def test_nearest_pixel_center_ties_choose_later_pixel():
    rgb = bytes(value for y in range(32) for x in range(32) for value in (x + y, x + y, x + y))
    result = encode_frame(frame(32, 32, rgb))
    assert result.u8 == bytes(2 * x + 2 * y + 2 for y in range(16) for x in range(16))


@settings(max_examples=60, deadline=None)
@given(st.integers(1, 90), st.integers(1, 90), st.binary(min_size=3, max_size=31))
def test_encoder_matches_independent_reference(width, height, pattern):
    rgb = (pattern * ((width * height * 3 + len(pattern) - 1) // len(pattern)))[:width * height * 3]
    result = encode_frame(frame(width, height, rgb))
    assert result.u8 == reference(width, height, rgb)
    assert len(result.observation.pixels) == 256
    assert all(math.isfinite(value) and 0 <= value <= 1 for value in result.observation.pixels)
    assert bytes(round(value * 255) for value in result.observation.pixels) == result.u8


@pytest.mark.parametrize("rgb", [b"", b"\x00\x00", b"\x00" * 4, bytearray(3), memoryview(bytes(3)), [0, 0, 0]])
def test_malformed_or_mutable_rgb_rejected(rgb):
    with pytest.raises(ValueError):
        frame(1, 1, rgb)


@pytest.mark.parametrize("change", [{"width": 0}, {"height": 8193}, {"width": True},
                                    {"pixel_format": "BGR24"}, {"receipt_monotonic_ms": float("nan")}])
def test_constructed_identity_cannot_bypass_validation(change):
    identity = frame(1, 1, bytes(3)).identity.model_copy(update=change)
    with pytest.raises(ValueError):
        RGBFrame(identity, bytes(3))


@pytest.mark.parametrize("width,height", [(8192, 1), (1, 8192), (1920, 1080)])
def test_large_or_extreme_aspect_ratio_stays_bounded(width, height):
    original = frame(width, height, bytes((255, 255, 255)) * (width * height))
    pair = preview_pair(original)
    assert len(pair.encoded.u8) == 256
    assert sum(value == 255 for value in pair.encoded.u8) >= 16
    assert pair.source.width <= 320 and pair.source.height <= 180
    assert len(pair.source.rgb) == pair.source.width * pair.source.height * 3 <= 320 * 180 * 3
    assert pair.source.identity == pair.encoded.frame == original.identity


def test_same_pixels_retain_distinct_timing_and_sequence_identity():
    first = frame(1, 1, bytes(3), sequence=1, receipt_monotonic_ms=1.0)
    second = frame(1, 1, bytes(3), sequence=2, receipt_monotonic_ms=2.0)
    a, b = preview_pair(first), preview_pair(second)
    assert a.encoded.sha256 == b.encoded.sha256
    assert a.encoded.frame != b.encoded.frame
    with pytest.raises(ValueError, match="same frame identity"):
        PreviewPair(a.source, b.encoded)


def test_encoded_observation_mutation_cannot_change_canonical_pixels():
    original = frame(1, 1, bytes((255, 255, 255)))
    encoded = encode_frame(original)
    encoded.observation.pixels[0] = 0
    assert encoded.observation.pixels[0] == 1.0 and encoded.u8[0] == 255
    with pytest.raises(FrozenInstanceError):
        original.rgb = bytes(3)


def test_fixture_determinism_identity_orientation_motion_and_visible_counter():
    a = fixture_frame(1, "test-session", 1)
    assert a == fixture_frame(1, "test-session", 1)
    b = fixture_frame(2, "test-session", 1, receipt_monotonic_ms=55.0)
    assert a.rgb != b.rgb
    assert b.identity.source_sequence == b.identity.sequence == 2
    assert b.identity.source_clock == "producer" and b.identity.receipt_monotonic_ms == 55.0
    assert a.identity.source_id == "fixture-pattern" and a.identity.evidence_kind == "fixture"
    assert a.rgb[:3] == bytes((255, 0, 0))
    assert a.rgb[(320 - 1) * 3:320 * 3] == bytes((0, 255, 0))
    assert a.rgb[(180 - 1) * 320 * 3:(180 - 1) * 320 * 3 + 3] == bytes((0, 0, 255))
    # Bottom glyph rows change with sequence as well as the moving shapes.
    assert a.rgb[160 * 320 * 3:] != b.rgb[160 * 320 * 3:]


def test_fixture_allocation_has_its_own_render_cap():
    with pytest.raises(ValueError, match="bounded"):
        fixture_frame(0, "test-session", 1, width=8192, height=8192)
