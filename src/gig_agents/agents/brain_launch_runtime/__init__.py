"""Brain launch runtime package.

This package composes brain manifests and roles into backend launch plans and
interactive session controllers.
"""

from .errors import (
    BackendExecutionError,
    BrainLaunchRuntimeError,
    GatewayAttachError,
    GatewayDiscoveryError,
    GatewayError,
    GatewayHttpError,
    GatewayNoLiveInstanceError,
    GatewayProtocolError,
    GatewayUnsupportedBackendError,
    LaunchPlanError,
    SchemaValidationError,
    SessionManifestError,
)
from .launch_plan import (
    LaunchPlanRequest,
    backend_for_tool,
    build_launch_plan,
    plan_role_injection,
)
from .loaders import (
    BlueprintBinding,
    RolePackage,
    load_blueprint,
    load_brain_manifest,
    load_brain_recipe_from_path,
    load_role_package,
)
from .manifest import load_session_manifest
from .models import (
    GatewayControlResult,
    InteractiveSession,
    LaunchPlan,
    RoleInjectionPlan,
    SessionControlResult,
    SessionEvent,
    SessionResult,
)
from .runtime import (
    RuntimeSessionController,
    resume_runtime_session,
    start_runtime_session,
)

__all__ = [
    "BackendExecutionError",
    "BlueprintBinding",
    "BrainLaunchRuntimeError",
    "GatewayAttachError",
    "GatewayControlResult",
    "GatewayDiscoveryError",
    "GatewayError",
    "GatewayHttpError",
    "GatewayNoLiveInstanceError",
    "GatewayProtocolError",
    "GatewayUnsupportedBackendError",
    "InteractiveSession",
    "LaunchPlan",
    "LaunchPlanError",
    "LaunchPlanRequest",
    "RoleInjectionPlan",
    "RolePackage",
    "RuntimeSessionController",
    "SchemaValidationError",
    "SessionControlResult",
    "SessionEvent",
    "SessionManifestError",
    "SessionResult",
    "backend_for_tool",
    "build_launch_plan",
    "load_blueprint",
    "load_brain_manifest",
    "load_brain_recipe_from_path",
    "load_role_package",
    "load_session_manifest",
    "plan_role_injection",
    "resume_runtime_session",
    "start_runtime_session",
]
