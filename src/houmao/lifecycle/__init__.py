"""Shared lifecycle timing contracts and ReactiveX helpers."""

from houmao.lifecycle.rx_lifecycle_kernel import (
    AnchoredCompletionSnapshot,
    AnchoredCompletionStatus,
    CompletionAuthorityMode,
    LifecycleObservation,
    PostSubmitEvidence,
    ReadinessLifecycleStatus,
    ReadinessSnapshot,
    TurnAnchor,
    TurnAnchorState,
    build_anchored_completion_pipeline,
    build_readiness_pipeline,
    normalize_projection_text,
)

__all__ = [
    "AnchoredCompletionSnapshot",
    "AnchoredCompletionStatus",
    "CompletionAuthorityMode",
    "LifecycleObservation",
    "PostSubmitEvidence",
    "ReadinessLifecycleStatus",
    "ReadinessSnapshot",
    "TurnAnchor",
    "TurnAnchorState",
    "build_anchored_completion_pipeline",
    "build_readiness_pipeline",
    "normalize_projection_text",
]
