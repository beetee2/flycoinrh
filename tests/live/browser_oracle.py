"""Independent vectorized golden encoder for the safe 320x180 browser source.

Only frame generation is shared. This does not call the production encoder,
neural model, capture backend, or filesystem storage.
"""
import json
import sys

import numpy as np

from flytrap.live.fixture import fixture_frame


def main():
    frame = json.load(sys.stdin)
    assert frame["source_id"] == "fixture-pattern"
    assert (frame["width"], frame["height"]) == (320, 180)
    source = fixture_frame(frame["sequence"], frame["session_id"], frame["generation"])
    rgb = np.frombuffer(source.rgb, dtype=np.uint8).reshape(180, 320, 3)
    # A 16:9 source fits as 16x9, centered with three black rows above and four
    # below. Each nearest center samples x/y = 10,30,... in the source.
    centers_x = np.arange(10, 320, 20)
    centers_y = np.arange(10, 180, 20)
    sampled = rgb[centers_y[:, None], centers_x].astype(np.int64)
    gray = np.floor((sampled @ np.array([77, 150, 29]) + 128) / 256).astype(np.uint8)
    output = np.zeros((16, 16), dtype=np.uint8)
    output[3:12] = gray
    print(json.dumps(output.reshape(-1).tolist()))


if __name__ == "__main__":
    main()
