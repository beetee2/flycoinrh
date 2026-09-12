"""Write exact development camera comparisons without loading a neural model."""

import argparse
from fractions import Fraction
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import subprocess

from PIL import Image, ImageDraw

from flytrap.arena.core import Q, Scene
from flytrap.arena.render import _samples, render
from flytrap.arena.tracking import sample_coordinates, samples


DEFAULT_OUTPUT = Path("artifacts/milestones/05/final-sensorimotor/inputs")
POSITIONS = (("start", 48, 76), ("bottom-middle", 48, 92), ("bottom-left", 4, 92),
             ("bottom-right", 92, 92), ("upper-left", 4, 4), ("upper-right", 92, 4),
             ("center", 48, 48))
CROPS = ("crop16_v1", "tracking16_v3")


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def scalar_coordinates(x_q, y_q, crop):
    """Independent rational camera/FOV oracle for each declared camera."""
    if crop == "crop16_v1":
        width, follow = 128, 1
    elif crop == "tracking16_v3":
        width, follow = 96, Fraction(1, 4)
    else:
        raise ValueError("Unknown camera version")

    def axis(position):
        center = 48 + (Fraction(position, Q) - 48) * follow
        return tuple(max(0, min(95, math.floor(center - width // 2 + Fraction(2*i+1, 32)*width)))
                     for i in range(16))

    return axis(x_q), axis(y_q)


def inspect_input(scene, raster, x_q, y_q, crop):
    xs, ys = scalar_coordinates(x_q, y_q, crop)
    oracle = bytes(raster[y*96+x] for y in ys for x in xs)
    actual = (_samples if crop == "crop16_v1" else samples)(raster, x_q=x_q, y_q=y_q)
    if actual != oracle:
        raise ValueError("Production sampling differs from the independent scalar oracle")
    if crop == "tracking16_v3" and sample_coordinates(x_q, y_q) != (xs, ys):
        raise ValueError("Candidate coordinates differ from the independent scalar oracle")
    pads = {}
    for side, pad in (("left", scene.left_pad), ("right", scene.right_pad)):
        indices = [j*16+i for j, y in enumerate(ys) for i, x in enumerate(xs)
                   if pad.x0 <= x < pad.x1 and pad.y0 <= y < pad.y1]
        values = sorted({actual[index] for index in indices})
        pads[side] = dict(sample_indices=indices, sample_count=len(indices), values=values,
                          bright_dark_contrast=values == [0, 255])
    return dict(crop=crop, sample_x=xs, sample_y=ys, pixels_u8=list(actual),
                observation_sha256=digest(actual), exact_oracle_match=True, pads=pads)


def draw_sheet(output, layout, raster, records):
    width, row_height = 756, 238
    sheet = Image.new("RGB", (width, 92 + len(records)*row_height), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 10), f"DEVELOPMENT INPUT COMPARISON: stripes on {layout}; no neural calls", fill="black")
    draw.text((12, 28), "Orange cross is a human display overlay, excluded from every controller input.", fill="black")
    draw.text((12, 46), "Inputs are exact 16 x 16 bytes enlarged using nearest-neighbor sampling.", fill="black")
    for x, text in ((12, "Canonical scene / sampling position"), (260, "Original crop16_v1"),
                    (508, "Candidate tracking16_v3")):
        draw.text((x, 70), text, fill="black")
    for index, record in enumerate(records):
        top = 92 + index*row_height
        name, x, y = record["name"], *record["position_pixels"]
        draw.text((12, top), f"{name}: ({x}, {y})", fill="black")
        canonical = Image.frombytes("L", (96, 96), raster).convert("RGB").resize(
            (192, 192), Image.Resampling.NEAREST)
        marker = ImageDraw.Draw(canonical)
        mx, my = x*2, y*2
        marker.line((mx-7, my, mx+7, my), fill="darkorange", width=3)
        marker.line((mx, my-7, mx, my+7), fill="darkorange", width=3)
        sheet.paste(canonical, (12, top+20))
        for column, crop in enumerate(CROPS, start=1):
            detail = record["inputs"][crop]
            image = Image.frombytes("L", (16, 16), bytes(detail["pixels_u8"]))
            sheet.paste(image.resize((192, 192), Image.Resampling.NEAREST).convert("RGB"),
                        (12 + column*248, top+20))
            counts = detail["pads"]
            draw.text((12 + column*248, top+216),
                      f"Pad samples L {counts['left']['sample_count']}, R {counts['right']['sample_count']}",
                      fill="black")
    path = output / f"{layout}-input-comparison.png"
    sheet.save(path)
    return path.name


def whole_region(scenes, rasters):
    starts = tuple(range(4*Q, 92*Q+1, 4*Q))
    # Check every legal coordinate, not just one arbitrary representative from
    # the camera's 23 bins. Each two-axis cell is a Cartesian product of these.
    grids = {start: scalar_coordinates(start, start, "tracking16_v3")[0] for start in starts}
    for position in range(4*Q, 92*Q+1):
        start = starts[(position - 4*Q) // (4*Q)]
        if sample_coordinates(position, position) != (grids[start], grids[start]):
            raise ValueError("A legal position is outside its declared quantization bin")
    bins = []
    minima = {layout: {side: 256 for side in ("left", "right")} for layout in scenes}
    all_contrast = all_difference = True
    for x_q in starts:
        for y_q in starts:
            details = {layout: inspect_input(scene, rasters[layout], x_q, y_q, "tracking16_v3")
                       for layout, scene in scenes.items()}
            difference = details["left"]["pixels_u8"] != details["right"]["pixels_u8"]
            contrast = all(detail["pads"][side]["bright_dark_contrast"]
                           for detail in details.values() for side in ("left", "right"))
            all_difference &= difference
            all_contrast &= contrast
            for layout, detail in details.items():
                for side in ("left", "right"):
                    minima[layout][side] = min(minima[layout][side], detail["pads"][side]["sample_count"])
            bins.append(dict(x_q_inclusive=[x_q, min(x_q+4*Q-1, 92*Q)],
                             y_q_inclusive=[y_q, min(y_q+4*Q-1, 92*Q)],
                             sample_x=details["left"]["sample_x"], sample_y=details["left"]["sample_y"],
                             both_layouts_both_pads_have_bright_dark_contrast=contrast,
                             layouts_have_different_pixels=difference,
                             layouts={layout: {key: detail[key] for key in ("pads", "observation_sha256")}
                                      for layout, detail in details.items()}))
    if not (all_contrast and all_difference):
        raise ValueError("Candidate failed complete operating-region texture visibility")
    return dict(operating_region_pixels=[4, 92], quantization_units_per_pixel=Q,
                checked_axis_q_positions=92*Q-4*Q+1, unique_axis_grids=len(set(grids.values())),
                camera_axis_bins=len(starts), camera_bin_pairs=len(bins),
                minimum_pad_sample_counts=minima, all_pad_contrasts_pass=all_contrast,
                all_layout_differences_pass=all_difference, bins=bins)


def generate(output):
    output.mkdir(parents=True, exist_ok=False)
    scenes = {"left": Scene("stripes", "checkerboard"), "right": Scene("checkerboard", "stripes")}
    rasters = {layout: render(scene) for layout, scene in scenes.items()}
    layouts = {}
    for layout, scene in scenes.items():
        raster = rasters[layout]
        (output / f"{layout}-canonical.gray").write_bytes(raster)
        Image.frombytes("L", (96, 96), raster).save(output / f"{layout}-canonical.png")
        records = []
        for name, x, y in POSITIONS:
            inputs = {crop: inspect_input(scene, raster, x*Q, y*Q, crop) for crop in CROPS}
            for crop, detail in inputs.items():
                stem = f"{layout}-{name}-{crop}"
                raw = bytes(detail["pixels_u8"])
                (output / f"{stem}.gray").write_bytes(raw)
                Image.frombytes("L", (16, 16), raw).save(output / f"{stem}.png")
                detail.update(raw_path=f"{stem}.gray", png_path=f"{stem}.png")
            records.append(dict(name=name, position_pixels=[x, y], position_q=[x*Q, y*Q], inputs=inputs))
        layouts[layout] = dict(left_texture=scene.left_texture, right_texture=scene.right_texture,
                               canonical_sha256=digest(raster), positions=records,
                               comparison_png=draw_sheet(output, layout, raster, records),
                               distinct_representative_inputs={crop: len({record["inputs"][crop]["observation_sha256"]
                                                                        for record in records}) for crop in CROPS})
    sources = ("scripts/feasibility_final_inputs.py", "flytrap/arena/render.py", "flytrap/arena/tracking.py",
               "flytrap/arena/core.py", "flytrap/contracts.py")
    report = dict(status="PASS", real_model_calls=0, synthetic_model_calls=0, layouts=layouts,
                  observation_versions=list(CROPS), development_only=True,
                  movement_feedback_quantization="tracking16_v3 shifts one sampled world pixel per four world pixels",
                  overlay_scope="Only the canonical display image has a position marker; raw raster and inputs do not.",
                  normalization="Observation float = sampled unsigned grayscale byte / 255; JSON preserves raw bytes.",
                  whole_region=whole_region(scenes, rasters),
                  environment=dict(python=platform.python_version(), pillow=importlib.metadata.version("Pillow")),
                  source_head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                  source_sha256={path: digest(Path(path).read_bytes()) for path in sources})
    save_json(output / "report.json", report)
    print(json.dumps(dict(status=report["status"], output=str(output), real_model_calls=0, synthetic_model_calls=0,
                          camera_bin_pairs=report["whole_region"]["camera_bin_pairs"],
                          minimum_pad_sample_counts=report["whole_region"]["minimum_pad_sample_counts"],
                          all_pad_contrasts_pass=report["whole_region"]["all_pad_contrasts_pass"],
                          all_layout_differences_pass=report["whole_region"]["all_layout_differences_pass"]),
                     sort_keys=True))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    generate(parser.parse_args().output)
