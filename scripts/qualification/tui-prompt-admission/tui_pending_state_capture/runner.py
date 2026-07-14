"""Orchestrator for one pending-state capture attempt."""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.models import (  # type: ignore[import-untyped]
    FixtureContract,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.paths import (  # type: ignore[import-untyped]
    LongHorizonRunPaths,
    initialize_owned_run_root,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.preflight import (  # type: ignore[import-untyped]
    PreparedProviderHome,
    prepare_provider_home,
    remove_sensitive_provider_home,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.projects import (  # type: ignore[import-untyped]
    prepare_boltons_project,
)
from houmao.demo.shared_tui_tracking_demo_pack.tooling import (  # type: ignore[import-untyped]
    build_tool_session_name,
    kill_tmux_session_if_exists,
    launch_tmux_session,
    resolve_active_pane_id,
)
from houmao.terminal_record.models import TerminalRecordPaths  # type: ignore[import-untyped]
from houmao.terminal_record.service import start_terminal_record, stop_terminal_record  # type: ignore[import-untyped]

from .freeze import file_digest, freeze_recording, save_frozen_evidence
from .labels import (
    analyze_snapshots,
    load_labels_file,
    load_snapshots,
    save_label_summary,
    save_labels_file,
)
from .lifecycle import LifecycleExecutor
from .models import LifecycleManifest, ProviderName, load_lifecycle_manifest
from .pattern_poller import TmuxPatternPoller
from .video import render_labels_video


BOLTONS_FIXTURE = FixtureContract(
    path="tests/fixtures/test-projects/boltons",
    upstream_revision="979fa9b613fa8c0a455ae16ea6f2ec91c11ecafe",
    expected_collection_count=437,
)
SAMPLE_INTERVAL_SECONDS = 0.05


@dataclass
class CaptureRunConfig:
    """Caller-provided configuration for one capture attempt."""

    provider: ProviderName
    run_root: Path
    lifecycle_path: Path | None = None
    attempt_id: int | None = None
    skip_video: bool = False


@dataclass
class CaptureRunResult:
    """Final result of one capture attempt."""

    success: bool
    attempt_dir: Path
    recording_root: Path
    labels_path: Path
    summary_path: Path
    frozen_evidence_path: Path
    video_path: Path | None
    taint_reasons: tuple[str, ...]
    transition_times: dict[str, float | None]


class TuiPendingStateCaptureRunner:
    """Run one tracker-blind prompt-queue lifecycle and freeze the evidence."""

    def __init__(self, *, repo_root: Path, config: CaptureRunConfig) -> None:
        self.m_repo_root = repo_root.resolve()
        self.m_config = config
        self.m_manifest: LifecycleManifest | None = None
        self.m_paths: LongHorizonRunPaths | None = None
        self.m_attempt_dir: Path | None = None
        self.m_recording_root: Path | None = None
        self.m_provider_home: PreparedProviderHome | None = None
        self.m_project_root: Path | None = None
        self.m_session_name: str | None = None
        self.m_pane_id: str | None = None
        self.m_taint_reasons: list[str] = []
        self.m_transition_times: dict[str, float | None] = {
            "active_onset": None,
            "pending_onset": None,
            "pending_offset": None,
            "done_onset": None,
            "ready_return": None,
        }
        self.m_recorder_started = False
        self.m_observed_pending_count: int | None = None

    def run(self) -> CaptureRunResult:
        """Execute the full capture workflow and return the result."""

        try:
            self._setup_paths()
            self._load_manifest()
            self._prepare_project()
            self._prepare_provider_home()
            self._launch_session()
            self._start_recorder()
            self._execute_lifecycle()
            self._stop_recorder()
            self._analyze_labels()
            if not self.m_config.skip_video:
                self._render_video()
            self._freeze()
        except Exception as exc:  # noqa: BLE001
            self._taint(f"capture_failed: {exc}")
            self._stop_recorder_safe()
            if (
                self.m_manifest is not None
                and self.m_attempt_dir is not None
                and self.m_recording_root is not None
            ):
                self._freeze()
            raise
        finally:
            self._cleanup()

        assert self.m_attempt_dir is not None
        assert self.m_recording_root is not None
        return CaptureRunResult(
            success=not self.m_taint_reasons,
            attempt_dir=self.m_attempt_dir,
            recording_root=self.m_recording_root,
            labels_path=self.m_attempt_dir / "labels" / "labels.json",
            summary_path=self.m_attempt_dir / "labels" / "labels-summary.json",
            frozen_evidence_path=self.m_attempt_dir / "capture" / "frozen-evidence.json",
            video_path=(
                self.m_attempt_dir / "review" / "labels.mp4"
                if not self.m_config.skip_video
                else None
            ),
            taint_reasons=tuple(self.m_taint_reasons),
            transition_times=dict(self.m_transition_times),
        )

    def dry_run_steps(self) -> list[dict[str, Any]]:
        """Return the resolved lifecycle steps without touching tmux."""

        self._load_manifest()
        assert self.m_manifest is not None
        return [self._step_to_payload(step) for step in self.m_manifest.steps]

    def _setup_paths(self) -> None:
        paths = LongHorizonRunPaths.from_requested_root(
            repo_root=self.m_repo_root,
            requested_root=self.m_config.run_root,
        )
        initialize_owned_run_root(
            paths=paths,
            suite_id="tui-pending-state-capture",
        )
        attempt_id = self._resolve_attempt_id(paths.run_root)
        self.m_attempt_id = attempt_id
        self.m_attempt_dir = paths.run_root / f"{self.m_config.provider}-attempt-{attempt_id:03d}"
        if self.m_attempt_dir.exists():
            raise RuntimeError(f"Attempt directory already exists: {self.m_attempt_dir}")
        self.m_attempt_dir.mkdir(parents=True, exist_ok=True)
        self.m_paths = paths
        self.m_recording_root = self.m_attempt_dir / "capture" / "recording"

    def _resolve_attempt_id(self, run_root: Path) -> int:
        if self.m_config.attempt_id is not None:
            return self.m_config.attempt_id
        existing = sorted(
            int(path.name.rsplit("-", 1)[-1])
            for path in run_root.glob(f"{self.m_config.provider}-attempt-*")
            if path.name.rsplit("-", 1)[-1].isdigit()
        )
        return (existing[-1] + 1) if existing else 1

    def _load_manifest(self) -> None:
        if self.m_manifest is not None:
            return
        if self.m_config.lifecycle_path is not None:
            manifest_path = self.m_config.lifecycle_path
        else:
            manifest_path = (
                self.m_repo_root
                / "scripts"
                / "qualification"
                / "tui-prompt-admission"
                / "lifecycles"
                / f"{self.m_config.provider}.json"
            )
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.m_manifest = load_lifecycle_manifest(payload)

    def _prepare_project(self) -> None:
        assert self.m_paths is not None
        project = prepare_boltons_project(
            repo_root=self.m_repo_root,
            paths=self.m_paths,
            fixture=BOLTONS_FIXTURE,
            cell_id="capture",
            attempt_number=self.m_attempt_id,
        )
        self.m_project_root = Path(project.copied_project_path)

    def _prepare_provider_home(self) -> None:
        assert self.m_paths is not None
        self.m_provider_home = prepare_provider_home(
            repo_root=self.m_repo_root,
            paths=self.m_paths,
            provider=self.m_config.provider,
            cell_id="capture",
            attempt_number=self.m_attempt_id,
        )

    def _launch_session(self) -> None:
        assert self.m_provider_home is not None
        assert self.m_project_root is not None
        assert self.m_attempt_dir is not None
        run_id = self.m_attempt_dir.name
        self.m_session_name = build_tool_session_name(tool=self.m_config.provider, run_id=run_id)
        launch_tmux_session(
            session_name=self.m_session_name,
            workdir=self.m_project_root,
            launch_script=self.m_provider_home.launch_helper_path,
            retain_shell_after_exit=True,
        )
        self.m_pane_id = resolve_active_pane_id(session_name=self.m_session_name)

    def _start_recorder(self) -> None:
        assert self.m_session_name is not None
        assert self.m_pane_id is not None
        assert self.m_recording_root is not None
        start_terminal_record(
            mode="active",
            target_session=self.m_session_name,
            target_pane=self.m_pane_id,
            tool=self.m_config.provider,
            run_root=self.m_recording_root,
            sample_interval_seconds=SAMPLE_INTERVAL_SECONDS,
        )
        self.m_recorder_started = True

    def _execute_lifecycle(self) -> None:
        assert self.m_manifest is not None
        assert self.m_session_name is not None
        assert self.m_pane_id is not None
        assert self.m_attempt_dir is not None
        poller = TmuxPatternPoller(
            m_session_name=self.m_session_name,
            m_pane_id=self.m_pane_id,
        )
        executor = LifecycleExecutor(
            manifest=self.m_manifest,
            poller=poller,
            start_monotonic=time.monotonic(),
        )
        result = executor.run()
        self.m_transition_times = result.transition_times
        for reason in result.taint_reasons:
            self._taint(reason)
        if not result.success:
            self._taint(result.failure_code or "lifecycle_failed")
            self._write_failure_note(result.failure_note, result.last_visible_text)

    def _stop_recorder(self) -> None:
        if not self.m_recorder_started or self.m_recording_root is None:
            return
        stop_terminal_record(run_root=self.m_recording_root)
        self.m_recorder_started = False

    def _stop_recorder_safe(self) -> None:
        if not self.m_recorder_started or self.m_recording_root is None:
            return
        try:
            stop_terminal_record(run_root=self.m_recording_root)
        except Exception as exc:  # noqa: BLE001
            self._taint(f"recorder_stop_failed: {exc}")
        finally:
            self.m_recorder_started = False

    def _analyze_labels(self) -> None:
        assert self.m_manifest is not None
        assert self.m_recording_root is not None
        assert self.m_attempt_dir is not None
        snapshots = load_snapshots(
            TerminalRecordPaths.from_run_root(run_root=self.m_recording_root).pane_snapshots_path
        )
        if not snapshots:
            self._taint("no_snapshots_for_labels")
            return
        labels, summary = analyze_snapshots(
            manifest=self.m_manifest,
            snapshots=snapshots,
        )
        labels_path = self.m_attempt_dir / "labels" / "labels.json"
        summary_path = self.m_attempt_dir / "labels" / "labels-summary.json"
        save_labels_file(path=labels_path, manifest=self.m_manifest, labels=labels)
        save_label_summary(path=summary_path, summary=summary)

        max_count: int | None = None
        for row in labels.values():
            if row.has_pending_message == "yes" and isinstance(row.pending_count, int):
                if max_count is None or row.pending_count > max_count:
                    max_count = row.pending_count
        self.m_observed_pending_count = max_count

        target = self.m_manifest.target_pending_count
        if target is not None:
            if max_count is None:
                self._taint(f"pending_count_capped_at_0_target_{target}")
            elif max_count < target:
                self._taint(f"pending_count_capped_at_{max_count}_target_{target}")

    def _render_video(self) -> None:
        assert self.m_recording_root is not None
        assert self.m_attempt_dir is not None
        snapshots_path = TerminalRecordPaths.from_run_root(
            run_root=self.m_recording_root
        ).pane_snapshots_path
        labels_path = self.m_attempt_dir / "labels" / "labels.json"
        if not snapshots_path.is_file() or not labels_path.is_file():
            self._taint("video_prerequisites_missing")
            return
        labels = load_labels_file(labels_path)
        output_path = self.m_attempt_dir / "review" / "labels.mp4"
        try:
            render_labels_video(
                snapshots_path=snapshots_path,
                labels=labels,
                output_path=output_path,
                fps=20,
            )
        except Exception as exc:  # noqa: BLE001
            self._taint(f"video_render_failed: {exc}")

    def _freeze(self) -> None:
        assert self.m_manifest is not None
        assert self.m_attempt_dir is not None
        assert self.m_recording_root is not None
        lifecycle_copy = self.m_attempt_dir / "capture" / "lifecycle-manifest.json"
        if self.m_config.lifecycle_path is not None:
            shutil.copy2(self.m_config.lifecycle_path, lifecycle_copy)
        else:
            default_path = (
                self.m_repo_root
                / "scripts"
                / "qualification"
                / "tui-prompt-admission"
                / "lifecycles"
                / f"{self.m_config.provider}.json"
            )
            shutil.copy2(default_path, lifecycle_copy)

        labels_path = self.m_attempt_dir / "labels" / "labels.json"
        summary_path = self.m_attempt_dir / "labels" / "labels-summary.json"
        video_path = self.m_attempt_dir / "review" / "labels.mp4"
        video_digest = file_digest(video_path) if video_path.is_file() else None

        evidence = freeze_recording(
            recording_root=self.m_recording_root,
            lifecycle_manifest_path=lifecycle_copy,
            labels_path=labels_path,
            labels_summary_path=summary_path,
            provider=self.m_manifest.provider,
            calibrated_version=self.m_manifest.calibrated_version,
            run_tainted=bool(self.m_taint_reasons),
            taint_reasons=tuple(self.m_taint_reasons),
            transition_times=dict(self.m_transition_times),
            observed_pending_count=self.m_observed_pending_count,
            target_pending_count=self.m_manifest.target_pending_count,
            video_digest=video_digest,
        )
        save_frozen_evidence(
            path=self.m_attempt_dir / "capture" / "frozen-evidence.json",
            evidence=evidence,
        )
        self._write_run_summary()

    def _write_run_summary(self) -> None:
        assert self.m_attempt_dir is not None
        assert self.m_manifest is not None
        summary = {
            "schema_version": 1,
            "provider": self.m_manifest.provider,
            "calibrated_version": self.m_manifest.calibrated_version,
            "attempt_dir": str(self.m_attempt_dir),
            "run_tainted": bool(self.m_taint_reasons),
            "taint_reasons": list(self.m_taint_reasons),
            "transition_times": dict(self.m_transition_times),
            "observed_pending_count": self.m_observed_pending_count,
            "target_pending_count": self.m_manifest.target_pending_count,
            "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        path = self.m_attempt_dir / "capture" / "run-summary.json"
        path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _write_failure_note(self, note: str | None, visible_text: str) -> None:
        assert self.m_attempt_dir is not None
        path = self.m_attempt_dir / "capture" / "failure-context.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"failure_note: {note or ''}", "--- visible_text ---", visible_text]
        path.write_text("\n".join(lines), encoding="utf-8")

    def _cleanup(self) -> None:
        if self.m_session_name is not None:
            try:
                kill_tmux_session_if_exists(session_name=self.m_session_name)
            except Exception as exc:  # noqa: BLE001
                self._taint(f"cleanup_session_failed: {exc}")
        if self.m_provider_home is not None and self.m_paths is not None:
            try:
                remove_sensitive_provider_home(
                    paths=self.m_paths,
                    prepared=self.m_provider_home,
                )
            except Exception as exc:  # noqa: BLE001
                self._taint(f"cleanup_provider_home_failed: {exc}")

    def _taint(self, reason: str) -> None:
        if reason not in self.m_taint_reasons:
            self.m_taint_reasons.append(reason)

    @staticmethod
    def _step_to_payload(step: Any) -> dict[str, Any]:
        from dataclasses import asdict

        payload = asdict(step)
        payload["kind"] = step.kind
        return payload
