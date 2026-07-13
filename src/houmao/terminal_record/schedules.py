"""Deterministic capture-delay schedules with authoritative source mappings."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Any, Literal, Sequence


SamplingMode = Literal["regular", "jittered", "bursty", "gapped"]


@dataclass(frozen=True)
class ScheduleSourceSample:
    """Minimal source sample used for schedule derivation."""

    sample_id: str
    elapsed_seconds: float


@dataclass(frozen=True)
class DerivedScheduleSample:
    """One target time mapped to the nearest authoritative source sample."""

    derived_sample_id: str
    target_elapsed_seconds: float
    source_sample_id: str
    source_elapsed_seconds: float

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible payload."""

        return asdict(self)


def derive_sample_schedule(
    *,
    samples: Sequence[ScheduleSourceSample],
    interval_seconds: float,
    sampling_mode: SamplingMode = "regular",
    phase_offset_seconds: float = 0.0,
    seed: int = 0,
) -> tuple[DerivedScheduleSample, ...]:
    """Map deterministic target times to nearest source samples without duplicates."""

    if not samples:
        return ()
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")
    if phase_offset_seconds < 0 or phase_offset_seconds >= interval_seconds:
        raise ValueError("phase_offset_seconds must be in [0, interval_seconds)")
    boundaries = derive_schedule_boundaries(
        first_elapsed=samples[0].elapsed_seconds,
        last_elapsed=samples[-1].elapsed_seconds,
        interval_seconds=interval_seconds,
        sampling_mode=sampling_mode,
        phase_offset_seconds=phase_offset_seconds,
        seed=seed,
    )
    selected: list[tuple[float, ScheduleSourceSample]] = []
    prior_id: str | None = None
    for target in boundaries:
        nearest = min(samples, key=lambda item: abs(item.elapsed_seconds - target))
        if nearest.sample_id != prior_id:
            selected.append((target, nearest))
            prior_id = nearest.sample_id
    return tuple(
        DerivedScheduleSample(
            derived_sample_id=f"d{index:06d}",
            target_elapsed_seconds=target,
            source_sample_id=source.sample_id,
            source_elapsed_seconds=source.elapsed_seconds,
        )
        for index, (target, source) in enumerate(selected, start=1)
    )


def derive_schedule_boundaries(
    *,
    first_elapsed: float,
    last_elapsed: float,
    interval_seconds: float,
    sampling_mode: SamplingMode,
    phase_offset_seconds: float = 0.0,
    seed: int = 0,
) -> tuple[float, ...]:
    """Return deterministic target times for fixed and irregular schedules."""

    if last_elapsed < first_elapsed:
        raise ValueError("last_elapsed must not precede first_elapsed")
    cursor = min(first_elapsed + phase_offset_seconds, last_elapsed)
    boundaries = [cursor]
    step_index = 0
    rng = random.Random(seed)
    while cursor < last_elapsed:
        if sampling_mode == "regular":
            multiplier = 1.0
        elif sampling_mode == "jittered":
            multiplier = rng.uniform(0.65, 1.35)
        elif sampling_mode == "bursty":
            multiplier = (0.35, 0.35, 0.35, 2.95)[step_index % 4]
        elif sampling_mode == "gapped":
            multiplier = (1.0, 1.0, 3.0, 1.0)[step_index % 4]
        else:
            raise ValueError(f"Unsupported sampling mode: {sampling_mode}")
        cursor += interval_seconds * multiplier
        boundaries.append(min(cursor, last_elapsed))
        step_index += 1
    return tuple(boundaries)
