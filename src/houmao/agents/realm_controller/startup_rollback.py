"""Own rollback actions for one uncommitted runtime launch."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, ExitStack, contextmanager
from contextvars import ContextVar
import json
from pathlib import Path
import subprocess

from houmao.agents.realm_controller.errors import RuntimeStartupRollbackError
from houmao.owned_mutation import remove_tree_or_path


class RuntimeStartup:
    """Keep cleanup actions and their evidence until required startup commits."""

    def __init__(self) -> None:
        """Initialize empty ownership receipts."""

        self.m_actions: list[tuple[str, Callable[[], None]]] = []
        self.m_directories: list[tuple[Path, int, int]] = []
        self.m_diagnostics: set[Path] = set()
        self.m_committed: bool = False
        self.m_registry_publication: tuple[str, str, str] | None = None
        self.m_terminal_ids: dict[tuple[str, str], str] = {}
        self.m_guards: ExitStack = ExitStack()

    def hold(self, guard: AbstractContextManager[None]) -> None:
        """Hold the birth's owner guard through required publication and rollback."""

        self.m_guards.enter_context(guard)

    def create_directory(self, path: Path) -> None:
        """Exclusively acquire a fresh runtime directory for this attempt."""

        if path.resolve() != path:
            raise ValueError("Startup directory must use its canonical owner-local path")
        path.mkdir(parents=True, mode=0o700)
        info = path.lstat()
        self.m_directories.append((path, info.st_dev, info.st_ino))

    def record_terminal(self, *, socket: str, session_name: str, session_id: str) -> None:
        """Bind publication targets to the terminal acquired for this birth."""

        self.m_terminal_ids[(socket, session_name)] = session_id

    def terminal_id(self, *, socket: str, session_name: str) -> str | None:
        """Return the tmux session ID captured from creation."""

        return self.m_terminal_ids.get((socket, session_name))

    def watch_registry_publication(
        self, *, registry_root: str, manifest_path: Path, generation_id: str
    ) -> None:
        """Capture the exact registry owner expected to publish during startup."""

        self.m_registry_publication = (registry_root, str(manifest_path), generation_id)

    def owns_registry_publication(
        self, *, registry_root: Path, manifest_path: str, generation_id: str
    ) -> bool:
        """Check whether the write is required publication for this attempt."""

        return self.m_registry_publication == (str(registry_root), manifest_path, generation_id)

    def add(self, description: str, action: Callable[[], None]) -> None:
        """Register a rollback action for an acquired resource."""

        self.m_actions.append((description, action))

    def retain_diagnostic(self, path: Path) -> None:
        """Keep a private startup log at the path reported in the launch error."""

        self.m_diagnostics.add(path)

    def commit(self) -> None:
        """End ownership of startup rollback before optional work starts."""

        self.m_committed = True
        self.m_actions.clear()
        self.m_directories.clear()
        self.m_diagnostics.clear()
        self.m_terminal_ids.clear()
        self.m_registry_publication = None
        self.release_guards()

    def release_guards(self) -> None:
        """Release the resources that serialize the startup transaction."""

        self.m_guards.close()

    def rollback(self) -> tuple[str, ...]:
        """Serialize rollback against manifest writers for the exact startup generation."""

        if self.m_registry_publication is None:
            return self._rollback_resources()
        from houmao.agents.realm_controller.manifest import _session_manifest_lock

        _, path, generation_id = self.m_registry_publication
        manifest_path = Path(path)
        try:
            with _session_manifest_lock(manifest_path):
                try:
                    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                except (FileNotFoundError, ValueError):
                    payload = None
                if (
                    isinstance(payload, dict)
                    and isinstance(observed := payload.get("registry_generation_id"), str)
                    and observed != generation_id
                ):
                    return ("runtime generation changed before cleanup",)
                return self._rollback_resources()
        except (OSError, RuntimeError) as error:
            return (f"runtime generation verification ({type(error).__name__})",)

    def _rollback_resources(self) -> tuple[str, ...]:
        """Release acquired resources in reverse order and retain evidence on failure."""

        failures: list[str] = []
        for description, action in reversed(self.m_actions):
            try:
                action()
            except Exception as error:
                failures.append(f"{description} ({type(error).__name__})")
        if failures:
            return tuple(failures)

        for path, device, inode in reversed(self.m_directories):
            try:
                info = path.lstat()
                if (info.st_dev, info.st_ino) == (device, inode):
                    self._remove_startup_artifacts(path)
            except FileNotFoundError:
                continue
            except Exception as error:
                failures.append(f"runtime launch artifacts ({type(error).__name__})")
        return tuple(failures)

    def _remove_startup_artifacts(self, path: Path) -> None:
        """Remove the acquired tree except its explicitly retained diagnostics."""

        if path in self.m_diagnostics:
            return
        if not path.is_symlink() and any(log.is_relative_to(path) for log in self.m_diagnostics):
            for child in path.iterdir():
                self._remove_startup_artifacts(child)
            return
        remove_tree_or_path(path, allowed_roots=(path.parent,))


_ACTIVE_STARTUP: ContextVar[RuntimeStartup | None] = ContextVar(
    "houmao_runtime_startup", default=None
)


def current_runtime_startup() -> RuntimeStartup | None:
    """Return the pending startup for the current launch, if any."""

    startup = _ACTIVE_STARTUP.get()
    return startup if startup is not None and not startup.m_committed else None


def stop_owned_startup_child(process: subprocess.Popen[bytes]) -> None:
    """Terminate and reap the child of this launch using its original handle."""

    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


@contextmanager
def runtime_startup_scope() -> Iterator[None]:
    """Rollback a failed launch inside its already-bound execution scope."""

    startup = RuntimeStartup()
    token = _ACTIVE_STARTUP.set(startup)
    try:
        yield
    except BaseException as error:
        failures = startup.rollback()
        if failures:
            if isinstance(error, Exception):
                raise RuntimeStartupRollbackError(error, failures) from error
            error.add_note(f"Incomplete launch cleanup: {', '.join(failures)}")
        raise
    finally:
        try:
            startup.release_guards()
        finally:
            _ACTIVE_STARTUP.reset(token)
