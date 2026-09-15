"""Pure RGB24 -> obs-rgb-letterbox16-v1. No device, model, or filesystem I/O.

Integer arithmetic defines half-up sizing and pixel-center sampling exactly,
including ties. RGB is full range, top-to-bottom, left-to-right, without stride.
The adapter must resolve YUV matrix/range before constructing an RGBFrame.
"""
from dataclasses import dataclass
from hashlib import sha256

from flytrap.contracts import Observation
from flytrap.live.contracts import FrameIdentity

MAX_FRAME_BYTES = 8192 * 8192 * 3
PREVIEW_WIDTH = 320
PREVIEW_HEIGHT = 180
ENCODER_ID = "obs-rgb-letterbox16-v1"


@dataclass(frozen=True, slots=True)
class RGBFrame:
    identity: FrameIdentity
    rgb: bytes

    def __post_init__(self):
        if type(self.identity) is not FrameIdentity:
            raise ValueError("a validated FrameIdentity is required")
        # Revalidate even model_construct/model_copy inputs before indexing bytes.
        FrameIdentity.model_validate(self.identity.model_dump())
        if type(self.rgb) is not bytes:
            raise ValueError("RGB storage must be immutable bytes")
        expected = self.identity.width * self.identity.height * 3
        if expected > MAX_FRAME_BYTES or len(self.rgb) != expected:
            raise ValueError("RGB byte count must exactly match bounded dimensions")


@dataclass(frozen=True, slots=True)
class EncodedFrame:
    frame: FrameIdentity
    u8: bytes
    sha256: str
    encoder_id: str = ENCODER_ID

    @property
    def observation(self) -> Observation:
        # Return a fresh model: Observation's list is mutable despite frozen=True.
        # Frame identity and timestamps never enter the controller's input.
        return Observation(schema_version="1", pixels=[value / 255 for value in self.u8])


@dataclass(frozen=True, slots=True)
class RGBPreview:
    identity: FrameIdentity
    width: int
    height: int
    rgb: bytes


@dataclass(frozen=True, slots=True)
class PreviewPair:
    source: RGBPreview
    encoded: EncodedFrame

    def __post_init__(self):
        if self.source.identity != self.encoded.frame:
            raise ValueError("source and encoded previews require the same frame identity")


def _fit(width: int, height: int, box_width: int, box_height: int) -> tuple[int, int]:
    # Choose one exact rational scale; floor(n/d + 1/2) is (2n+d)//2d.
    if box_width * height <= box_height * width:
        numerator, denominator = box_width, width
    else:
        numerator, denominator = box_height, height
    return (max(1, (2 * width * numerator + denominator) // (2 * denominator)),
            max(1, (2 * height * numerator + denominator) // (2 * denominator)))


def _source_coordinate(destination: int, source_size: int, resized_size: int) -> int:
    return min(source_size - 1, ((2 * destination + 1) * source_size) // (2 * resized_size))


def encode_frame(frame: RGBFrame) -> EncodedFrame:
    """Whole-source letterbox, BT.601 integer grayscale, and exact uint8 hash."""
    if type(frame) is not RGBFrame:
        raise ValueError("encoder requires an RGBFrame")
    width, height = frame.identity.width, frame.identity.height
    resized_width, resized_height = _fit(width, height, 16, 16)
    left, top = (16 - resized_width) // 2, (16 - resized_height) // 2
    output = bytearray(256)
    for y in range(resized_height):
        source_y = _source_coordinate(y, height, resized_height)
        for x in range(resized_width):
            source_x = _source_coordinate(x, width, resized_width)
            offset = (source_y * width + source_x) * 3
            red, green, blue = frame.rgb[offset:offset + 3]
            output[(top + y) * 16 + left + x] = (77 * red + 150 * green + 29 * blue + 128) // 256
    values = bytes(output)
    return EncodedFrame(frame=frame.identity, u8=values, sha256=sha256(values).hexdigest())


def preview_pair(frame: RGBFrame) -> PreviewPair:
    """Ephemeral source thumbnail and exact encoder output from the same frame.

    The caller owns explicit preview consent and expiry. No pixels are persisted.
    Small sources retain their dimensions; larger sources fit inside 320 x 180.
    """
    encoded = encode_frame(frame)
    width, height = frame.identity.width, frame.identity.height
    if width <= PREVIEW_WIDTH and height <= PREVIEW_HEIGHT:
        preview_width, preview_height = width, height
        rgb = frame.rgb
    else:
        preview_width, preview_height = _fit(width, height, PREVIEW_WIDTH, PREVIEW_HEIGHT)
        thumbnail = bytearray(preview_width * preview_height * 3)
        for y in range(preview_height):
            source_y = _source_coordinate(y, height, preview_height)
            for x in range(preview_width):
                source_x = _source_coordinate(x, width, preview_width)
                source_offset = (source_y * width + source_x) * 3
                target_offset = (y * preview_width + x) * 3
                thumbnail[target_offset:target_offset + 3] = frame.rgb[source_offset:source_offset + 3]
        rgb = bytes(thumbnail)
    return PreviewPair(RGBPreview(frame.identity, preview_width, preview_height, rgb), encoded)
