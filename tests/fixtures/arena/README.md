# Renderer fixtures

These synthetic fixtures test arena mechanics and make no model-performance
claim. `stripes_left_all_obstacles.gray` is 9,216 raw grayscale bytes in row-major
order, independently assembled from explicit row bands: a four-pixel black wall,
128 background, stripes on the left, checkerboard on the right, and all three
white distraction bars. `golden.json` freezes its SHA256 and independently
calculated 256-byte observation hashes at the start, two clipped corners, and a
fractional center. Fixture construction did not call the production renderer or
crop functions. Observation hashes cover sampled raw bytes before division by 255.

The tests also check individual boundary pixels, swapped texture differences,
subpixel floor sampling on a distinct synthetic ramp, and lossless PNG decoding.
