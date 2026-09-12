"""Bounded local laboratory request and result contracts."""
import hashlib
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SEEDS = (17, 29, 43)
CALL_CAP = 256
CALLS_PER_COMPARISON = 9
MOTORS = ("steer_L", "steer_R", "fwd_L", "fwd_R", "back", "stop", "click")
Byte = Annotated[int, Field(strict=True, ge=0, le=255)]
Count = Annotated[int, Field(strict=True, ge=0, le=10**12)]
Rate = Annotated[float, Field(ge=0, le=1e12)]
Pixels = Annotated[list[Byte], Field(min_length=256, max_length=256)]
Counts = Annotated[list[Count], Field(min_length=256, max_length=256)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class LabRequest(Contract):
    schema_version: Literal["flytrap-lab-request-1"]
    a: Pixels
    b: Pixels


class Rates(Contract):
    steer_L: Rate
    steer_R: Rate
    fwd_L: Rate
    fwd_R: Rate
    back: Rate
    stop: Rate
    click: Rate


class Statistics(Contract):
    sampled_neurons: Count
    spike_count: Count
    firing: Count
    spikes_per_sec: Rate
    mean_mv: Annotated[float, Field(ge=-1000, le=1000)]
    visual: Count
    motor: Count


class Sample(Contract):
    side: Literal["A", "A_repeat", "B"]
    seed: Literal[17, 29, 43]
    motor_rates_hz: Rates
    statistics: Statistics
    neural_ms: Literal[20.0]


class Population(Contract):
    neuron_indices: Annotated[list[Count], Field(min_length=1, max_length=10000)]
    body_ids: Annotated[list[Count], Field(min_length=1, max_length=10000)]
    pixel_indices: Annotated[list[Byte], Field(min_length=1, max_length=10000)]
    sampled_pixels_u8: Annotated[list[Byte], Field(min_length=1, max_length=10000)]
    drive_hz: Annotated[list[Rate], Field(min_length=1, max_length=10000)]
    coverage_counts: Counts
    missing_coordinates: Count

    @model_validator(mode="after")
    def aligned(self):
        if len({len(self.neuron_indices), len(self.body_ids), len(self.pixel_indices),
                len(self.sampled_pixels_u8), len(self.drive_hz)}) != 1:
            raise ValueError("retinal arrays must align")
        counts = [0] * 256
        for pixel in self.pixel_indices:
            counts[pixel] += 1
        if counts != self.coverage_counts:
            raise ValueError("coverage counts must match actual sample assignments")
        return self


class Populations(Contract):
    L1: Population
    L2: Population


class Retina(Contract):
    populations: Populations
    union_coverage_counts: Counts
    sampled_pixel_count: Annotated[int, Field(strict=True, ge=1, le=256)]
    discarded_pixel_indices: Annotated[list[Byte], Field(max_length=256)]


    @model_validator(mode="after")
    def coverage(self):
        expected = [a + b for a, b in zip(self.populations.L1.coverage_counts,
                                          self.populations.L2.coverage_counts)]
        if self.union_coverage_counts != expected:
            raise ValueError("combined coverage must equal L1 plus L2")
        if self.sampled_pixel_count != sum(count > 0 for count in expected):
            raise ValueError("sampled pixel count must match coverage")
        if self.discarded_pixel_indices != [i for i, count in enumerate(expected) if not count]:
            raise ValueError("discarded pixels must be the ordered coverage complement")
        return self


class Retinas(Contract):
    A: Retina
    B: Retina


class Metric(Contract):
    a_mean: Rate
    b_mean: Rate
    a_sd: Rate
    b_sd: Rate
    delta_mean: float
    delta_sd: Rate
    paired_deltas: Annotated[list[float], Field(min_length=3, max_length=3)]


class Metrics(Contract):
    steer_L: Metric
    steer_R: Metric
    fwd_L: Metric
    fwd_R: Metric
    back: Metric
    stop: Metric
    click: Metric


class Brightness(Contract):
    A: Annotated[float, Field(ge=0, le=255)]
    B: Annotated[float, Field(ge=0, le=255)]


class Comparison(Contract):
    same_image: bool
    equal_brightness: bool
    mean_brightness_u8: Brightness
    same_seed_repeatable: bool
    motor_rates_hz: Metrics


Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class InputHashes(Contract):
    A: Digest
    B: Digest


class Identities(Contract):
    model: dict
    graph_manifest_sha256: Digest
    source_head: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    source_sha256: dict[str, Digest]
    source_tree_sha256: Digest
    runtime: dict
    input_sha256: InputHashes
    encoding: str
    comparison: str
    statistics: str
    limitations: str


class LabResult(Contract):
    schema_version: Literal["flytrap-lab-result-1"]
    result_id: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
    created_at: str
    cached: Literal[False]
    fixture: Literal[False]
    request: LabRequest
    seeds: Annotated[list[Literal[17, 29, 43]], Field(min_length=3, max_length=3)]
    samples: Annotated[list[Sample], Field(min_length=9, max_length=9)]
    retina: Retinas
    comparison: Comparison
    identities: Identities
    attempted_calls: Annotated[int, Field(strict=True, ge=9, le=256)]

    @model_validator(mode="after")
    def paired(self):
        if self.seeds != list(SEEDS):
            raise ValueError("fixed matched seeds required")
        if [(s.seed, s.side) for s in self.samples] != [
                (seed, side) for seed in SEEDS for side in ("A", "A_repeat", "B")]:
            raise ValueError("each matched seed requires A, A repeat, B")
        for side, pixels in (("A", self.request.a), ("B", self.request.b)):
            if getattr(self.identities.input_sha256, side) != hashlib.sha256(bytes(pixels)).hexdigest():
                raise ValueError("input hash must identify exact submitted bytes")
            populations = getattr(self.retina, side).populations
            for name in ("L1", "L2"):
                pop = getattr(populations, name)
                if pop.sampled_pixels_u8 != [pixels[i] for i in pop.pixel_indices]:
                    raise ValueError("retinal samples must match submitted pixels")
                other = getattr(self.retina.A.populations, name)
                for field in ("neuron_indices", "body_ids", "pixel_indices", "coverage_counts", "missing_coordinates"):
                    if getattr(pop, field) != getattr(other, field):
                        raise ValueError("A and B must use identical retinal mapping")
        c = self.comparison
        if (c.same_image != (self.request.a == self.request.b)
                or c.equal_brightness != (sum(self.request.a) == sum(self.request.b))
                or c.mean_brightness_u8.A != sum(self.request.a) / 256
                or c.mean_brightness_u8.B != sum(self.request.b) / 256):
            raise ValueError("comparison controls must describe the submitted inputs")
        return self
