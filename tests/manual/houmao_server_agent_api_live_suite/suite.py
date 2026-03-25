"""Compatibility shim for the moved Houmao-server agent API demo pack.

The canonical implementation now lives under
`scripts/demo/houmao-server-agent-api-demo-pack/` and
`src/houmao/demo/houmao_server_agent_api_demo_pack/`. This module keeps the
legacy `tests/manual/...` imports working while delegating to the demo-pack
implementation.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

from houmao.demo.houmao_server_agent_api_demo_pack.commands import (
    auto_demo,
    default_expected_report_path,
    resolve_pack_paths,
)
from houmao.demo.houmao_server_agent_api_demo_pack.provisioning import (
    ArtifactRecorder,
    FixturePaths,
    LANE_IDS,
    LaneDefinition,
    LaneRuntime,
    SuiteConfig,
    SuiteError,
    _build_suite_paths,
    _choose_port,
    _cleanup_lanes,
    _is_observable_post_request_progress,
    _lane_fixture_report,
    _resolve_fixture_paths,
    _resolve_selected_lanes,
    _run_preflight,
    _start_suite_server,
    _state_signature,
    _stop_suite_server,
    _submit_interrupt_and_verify,
    _submit_prompt_and_verify,
    _timestamp_slug,
    _verify_lane_routes,
    _verify_shared_routes,
)
from houmao.server.client import HoumaoServerClient


def _repo_root() -> Path:
    """Return the repository root for the legacy manual shim."""

    return Path(__file__).resolve().parents[3]


def run_suite(config: SuiteConfig) -> dict[str, Any]:
    """Run the canonical demo-pack `auto` flow through the legacy shim."""

    pack_paths = resolve_pack_paths(repo_root=_repo_root())
    if config.output_root is not None:
        demo_output_dir = config.output_root.resolve()
    else:
        demo_output_dir = (pack_paths.runs_dir / f"legacy-manual-shim-{_timestamp_slug()}").resolve()
    auto_demo(
        pack_paths=pack_paths,
        demo_output_dir=demo_output_dir,
        config=SuiteConfig(
            selected_lane_ids=config.selected_lane_ids,
            pack_dir=pack_paths.pack_dir,
            output_root=demo_output_dir,
            port=config.port,
            compat_http_timeout_seconds=config.compat_http_timeout_seconds,
            compat_create_timeout_seconds=config.compat_create_timeout_seconds,
            compat_provider_ready_timeout_seconds=config.compat_provider_ready_timeout_seconds,
            health_timeout_seconds=config.health_timeout_seconds,
            prompt_timeout_seconds=config.prompt_timeout_seconds,
            prompt_poll_interval_seconds=config.prompt_poll_interval_seconds,
            history_limit=config.history_limit,
        ),
        expected_report_path=default_expected_report_path(pack_paths.pack_dir),
        snapshot=False,
    )
    return {
        "suite": "houmao-server-agent-api-live-suite-shim",
        "run_root": str(demo_output_dir),
        "selected_lanes": [lane.lane_id for lane in _resolve_selected_lanes(config.selected_lane_ids)],
    }


__all__ = [
    "ArtifactRecorder",
    "FixturePaths",
    "HoumaoServerClient",
    "LANE_IDS",
    "LaneDefinition",
    "LaneRuntime",
    "SuiteConfig",
    "SuiteError",
    "_build_suite_paths",
    "_choose_port",
    "_cleanup_lanes",
    "_is_observable_post_request_progress",
    "_lane_fixture_report",
    "_resolve_fixture_paths",
    "_resolve_selected_lanes",
    "_run_preflight",
    "_start_suite_server",
    "_state_signature",
    "_stop_suite_server",
    "_submit_interrupt_and_verify",
    "_submit_prompt_and_verify",
    "_timestamp_slug",
    "_verify_lane_routes",
    "_verify_shared_routes",
    "run_suite",
    "subprocess",
]
