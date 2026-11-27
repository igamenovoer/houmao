"""Check the private broker and the stock Hermes session hook payload."""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Event, Thread
from time import monotonic, sleep
from types import SimpleNamespace

import pytest

from houmao.agents.realm_controller import hermes_self, hermes_tool_origin
from houmao.agents.realm_controller.assets import hermes_tool_origin as native_hook
from houmao.agents.realm_controller.errors import SessionManifestError


def test_hook_payload_is_private_and_idempotent(tmp_path: Path) -> None:
    """Reject a conflicting native hook file instead of adopting or replacing it."""

    broker = hermes_tool_origin.hermes_tool_origin_socket(tmp_path, "owner")
    assert len(os.fsencode(broker)) < 108
    hermes_tool_origin.install_hermes_tool_origin_hook(tmp_path, broker_socket=broker)
    hermes_tool_origin.install_hermes_tool_origin_hook(tmp_path, broker_socket=broker)
    native_dir = tmp_path / "plugins" / hermes_tool_origin.HERMES_TOOL_ORIGIN_PLUGIN
    assert native_dir.stat().st_mode & 0o077 == 0
    assert all(path.stat().st_mode & 0o077 == 0 for path in native_dir.iterdir())
    (native_dir / "broker-socket").write_text("/tmp/unowned.sock\n")
    with pytest.raises(ValueError, match="origin is unavailable"):
        hermes_tool_origin.install_hermes_tool_origin_hook(tmp_path, broker_socket=broker)


@pytest.mark.skipif(not hasattr(socket, "SO_PEERCRED"), reason="needs kernel Unix peer identity")
def test_broker_attributes_stock_hook_to_its_gateway_and_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject another peer, a copied profile proof, and a renewed authority or expired proof."""

    current = Event()
    current.set()
    pid = os.getpid()
    birth = hermes_tool_origin._dispatch_origin_birth_token(pid)
    assert birth is not None
    root = tmp_path / "hermes"
    scope = hermes_tool_origin._BrokerScope(root, "owner", pid, birth)
    selected_home = root / "profiles" / "one"
    sibling_home = root / "profiles" / "two"
    profile_epochs = {"one": 1, "two": 1}
    active_home = selected_home
    active_session = "one"
    now = 1
    monkeypatch.setattr(
        hermes_tool_origin,
        "_dispatch_origin_birth_token",
        lambda _: birth if current.is_set() else None,
    )
    monkeypatch.setattr(hermes_tool_origin.time, "monotonic_ns", lambda: now)

    def auth(home: Path, session: str, **binding: object) -> SimpleNamespace:
        """Represent two published profile bindings on the same gateway PID."""

        if (home, session) not in ((selected_home, "one"), (sibling_home, "two")):
            raise SessionManifestError("wrong native session")
        return SimpleNamespace(
            home=str(home),
            native_session_id=session,
            broker_socket=str(binding["broker_socket"]),
            fingerprint=f"{session}:{profile_epochs[session]}",
        )

    monkeypatch.setattr(hermes_self, "load_hermes_tool_authority", auth)
    with TemporaryDirectory(prefix="houmao-origin-test-", dir="/tmp") as scratch:
        path = Path(scratch) / "origin.sock"
        monkeypatch.setattr(hermes_tool_origin, "hermes_tool_origin_socket", lambda *_: path)
        broker = Thread(target=hermes_tool_origin._serve, args=(scope,), daemon=True)
        broker.start()
        try:
            deadline = monotonic() + 3
            while hermes_tool_origin._current_broker_pid(scope) is None:
                assert monotonic() < deadline
                sleep(0.01)

            # Exercise the packaged resolver with the native API's callback inputs.
            monkeypatch.setattr(native_hook, "__file__", str(tmp_path / "__init__.py"))
            (tmp_path / "broker-socket").write_text(f"{path}\n")
            monkeypatch.setitem(
                sys.modules,
                "hermes_constants",
                SimpleNamespace(
                    get_hermes_home_override=lambda: str(active_home),
                    hermes_home_key=lambda: str(active_home),
                ),
            )
            monkeypatch.setitem(
                sys.modules,
                "gateway.session_context",
                SimpleNamespace(bound_session_env=lambda _: active_session),
            )
            resolver = []
            native_hook.register(
                SimpleNamespace(register_session_env=lambda names, fn: resolver.append((names, fn)))
            )
            names, run_hook = resolver[0]
            assert names == [hermes_tool_origin.HERMES_TOOL_ORIGIN_ENV]
            raw = run_hook("one")[names[0]]
            assert isinstance(raw, str)
            assert run_hook("two") == {names[0]: None}
            monkeypatch.setenv("HERMES_SESSION_ID", "one")
            active_session = ""
            assert run_hook("one") == {names[0]: None}
            one = auth(selected_home, "one", broker_socket=path)
            two = auth(sibling_home, "two", broker_socket=path)
            active_session, active_home = "two", sibling_home
            sibling = run_hook("two")[names[0]]
            assert isinstance(sibling, str) and sibling != raw
            hermes_tool_origin.require_hermes_tool_origin(two, sibling)
            hermes_tool_origin.require_hermes_tool_origin(one, raw)
            with pytest.raises(SessionManifestError, match="origin is unavailable") as refused:
                hermes_tool_origin.require_hermes_tool_origin(two, raw)
            assert raw not in str(refused.value)

            unauthorized = {"op": "issue", "home": str(selected_home), "session": "one"}
            script = (
                "import socket, sys; peer = socket.socket(socket.AF_UNIX); "
                "peer.connect(sys.argv[1]); peer.sendall(sys.argv[2].encode() + b'\\n'); "
                "sys.stdout.buffer.write(peer.makefile('rb').readline())"
            )
            response = subprocess.check_output(
                [sys.executable, "-c", script, str(path), json.dumps(unauthorized)], timeout=3
            )
            assert response == b"null\n"

            profile_epochs["one"] += 1
            with pytest.raises(SessionManifestError, match="origin is unavailable"):
                hermes_tool_origin.require_hermes_tool_origin(one, raw)
            hermes_tool_origin.require_hermes_tool_origin(two, sibling)
            active_session, active_home = "one", selected_home
            new = auth(selected_home, "one", broker_socket=path)
            renewed = run_hook("one")[names[0]]
            hermes_tool_origin.require_hermes_tool_origin(new, renewed)
            now += hermes_tool_origin._LIFETIME_NS
            with pytest.raises(SessionManifestError, match="origin is unavailable"):
                hermes_tool_origin.require_hermes_tool_origin(new, renewed)
        finally:
            current.clear()
            broker.join(timeout=3)
        assert not broker.is_alive()
        assert not path.exists()
