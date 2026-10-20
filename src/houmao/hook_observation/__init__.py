"""Provider-neutral CLI hook observation channel primitives.

This package owns the raw event envelope and session store, the Claude and
Codex event normalizers, and the pure hook-posture reducer. Collector
transport, the command emitter, and observer settings generation are separate
modules in the same package.
"""

from houmao.hook_observation.codex_normalizer import (
    CodexEventNormalizer,
    CodexNormalizerSummary,
)
from houmao.hook_observation.models import (
    HookAdapter,
    HookEventEnvelope,
    HookObservation,
    HookPosture,
    HookPostureCounters,
    HookPostureDiagnostic,
    HookPresence,
)
from houmao.hook_observation.normalizer import (
    MAX_PROVIDER_EVENT_BYTES,
    normalize_envelope,
    normalize_provider_event,
)
from houmao.hook_observation.reducer import HookPostureReducer, build_hook_posture_pipeline
from houmao.hook_observation.store import (
    HookObservationStore,
    parse_envelope_line,
    read_store,
)


__all__ = [
    "MAX_PROVIDER_EVENT_BYTES",
    "CodexEventNormalizer",
    "CodexNormalizerSummary",
    "HookAdapter",
    "HookEventEnvelope",
    "HookObservation",
    "HookObservationStore",
    "HookPosture",
    "HookPostureCounters",
    "HookPostureDiagnostic",
    "HookPostureReducer",
    "HookPresence",
    "build_hook_posture_pipeline",
    "normalize_envelope",
    "normalize_provider_event",
    "parse_envelope_line",
    "read_store",
]
