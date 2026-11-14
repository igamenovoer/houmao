"""OS-owned online admission survives competing controls and controller crashes."""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path
from typing import Any

import pytest

from houmao.mailbox.online_authority import OnlineConnectionAuthority
from houmao.mailbox.online_models import OnlineAuthorityContext, OnlineBindingError
from tests.unit.agents.realm_controller.test_mailbox_binding_authority import _manifest


def _hold_lease(path: str, ready: Any, release: Any) -> None:
    """Hold a real shared lease until the test permits completion."""
    authority = OnlineConnectionAuthority.from_context(
        OnlineAuthorityContext(Path(path), "agent-a", "session-a")
    )
    with authority._lease("admission.lock", shared=True, deadline=time.monotonic() + 5):
        ready.set()
        release.wait(10)


def _orphan_intent(path: str, ready: Any) -> None:
    """Remain in an active controller until the parent kills the process."""
    authority = OnlineConnectionAuthority.from_context(
        OnlineAuthorityContext(Path(path), "agent-a", "session-a")
    )
    revision, _ = authority.snapshot()
    with authority.control(expected_revision=revision.revision, timeout_seconds=5):
        ready.set()
        time.sleep(20)


def test_cross_process_retirement_times_out_without_false_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3]))
    path = _manifest(tmp_path)
    authority = OnlineConnectionAuthority.from_context(
        OnlineAuthorityContext(path, "agent-a", "session-a")
    )
    slot, _ = authority.snapshot()
    authority._reconcile(time.monotonic() + 1)
    epoch = authority.state()["epoch_id"]
    context = multiprocessing.get_context("spawn")
    ready, release = context.Event(), context.Event()
    child = context.Process(target=_hold_lease, args=(str(path), ready, release))
    child.start()
    try:
        assert ready.wait(5)
        with pytest.raises(OnlineBindingError) as exc:
            with authority.control(expected_revision=slot.revision, timeout_seconds=0.1):
                pytest.fail("An admitted operation must drain before activation")
        assert exc.value.code == "online_retirement_busy" and exc.value.uncertain
        assert authority.snapshot()[0].revision == slot.revision
        assert authority.state()["epoch_id"] == epoch
        assert authority.state()["closing"] is False
    finally:
        release.set()
        child.join(5)
        if child.is_alive():
            child.kill()
            child.join()
    assert child.exitcode == 0
    with authority.control(expected_revision=slot.revision, timeout_seconds=1):
        authority.advance_epoch()
    assert authority.state()["epoch_id"] != epoch


def test_crashed_control_intent_reconciles_with_current_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3]))
    path = _manifest(tmp_path)
    authority = OnlineConnectionAuthority.from_context(
        OnlineAuthorityContext(path, "agent-a", "session-a")
    )
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    child = context.Process(target=_orphan_intent, args=(str(path), ready))
    child.start()
    try:
        assert ready.wait(5)
        assert authority.state()["closing"] is True
        with pytest.raises(OnlineBindingError):
            authority._reconcile(time.monotonic() + 0.1)
    finally:
        child.kill()
        child.join(5)
    authority._reconcile(time.monotonic() + 1)
    assert authority.state()["closing"] is False
    assert authority.state()["revision"] == authority.snapshot()[0].revision
