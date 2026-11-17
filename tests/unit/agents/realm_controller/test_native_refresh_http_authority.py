"""Fence native HTTP controls when listeners or executions change after selection."""

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest

from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_client import GatewayClient, GatewayEndpoint
from houmao.agents.realm_controller.native_refresh_models import (
    NativeHomeV1,
    NativeRefreshRequestV1,
    NativeRefreshResultV1,
    native_home_etag,
)
from tests.unit.agents.realm_controller.test_dsh_web_gateway import _runtime
from tests.unit.agents.realm_controller.test_gateway_native_refresh import (
    _bind_native,
    _http_client,
    _observation,
)


@pytest.mark.parametrize("path", ["/v1/native-home", "/v1/control/refresh"])
def test_conditional_native_get_refuses_changed_execution_before_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    """A stale captured authority cannot read a replacement gateway's resource state."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    home = _observation().home
    monkeypatch.setattr(runtime, "native_home", lambda: home)
    observation = Mock()
    monkeypatch.setattr(runtime, "observe_common_plugins", observation)
    client = _http_client(runtime, tmp_path, monkeypatch)
    response = client.get(path, headers={"If-Match": '"stale-execution"'})
    assert response.status_code == 412
    observation.assert_not_called()


def test_conditional_get_cannot_return_a_superseded_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing native authority during a state read cannot relabel its evidence."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    home = _observation().home
    monkeypatch.setattr(runtime, "native_home", lambda: home)
    other = _observation(home=home.model_copy(update={"agent_id": "other"}))
    monkeypatch.setattr(runtime, "observe_common_plugins", lambda: other)
    response = _http_client(runtime, tmp_path, monkeypatch).get(
        "/v1/control/refresh", headers={"If-Match": native_home_etag(home)}
    )
    assert response.status_code == 412


@pytest.mark.parametrize("matched", [False, True])
def test_conditional_post_checks_authority_inside_bounded_observe_first_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, matched: bool
) -> None:
    """Even no-op POSTs enforce the caller-captured execution before planning."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    observation = _observation("current")
    _bind_native(runtime, monkeypatch, observation)
    expected = observation.home.model_copy(update={} if matched else {"agent_id": "other"})
    response = _http_client(runtime, tmp_path, monkeypatch).post(
        "/v1/control/refresh", json={}, headers={"If-Match": native_home_etag(expected)}
    )
    assert response.status_code == (200 if matched else 412)
    if matched:
        assert response.json()["outcome"] == "already_current"


@pytest.mark.parametrize("operation", ["home", "check", "refresh"])
@pytest.mark.parametrize("changed", [False, True])
def test_bound_client_sends_precondition_and_refuses_other_execution_evidence(
    operation: str, changed: bool
) -> None:
    """Both request headers and returned home identities retain the selected authority."""

    selected = _observation("current")
    actual = selected.model_copy(
        update={"home": selected.home.model_copy(update={"agent_id": "other"})} if changed else {}
    )
    payload: NativeHomeV1 | NativeRefreshResultV1 = actual.home
    if operation == "refresh":
        payload = NativeRefreshResultV1(
            method="noop", outcome="already_current", observation=actual
        )
    encoded = (actual if operation == "check" else payload).model_dump_json().encode()
    client = GatewayClient(endpoint=GatewayEndpoint(host="127.0.0.1", port=43000))
    client.bind_native_home(selected.home)
    client.m_opener = Mock()
    client.m_opener.open.return_value = BytesIO(encoded)

    def invoke() -> object:
        """Use each public client surface with the same captured native execution."""

        if operation == "home":
            return client.get_native_home()
        if operation == "check":
            return client.get_common_plugin_state()
        return client.refresh_native(NativeRefreshRequestV1())

    if changed:
        with pytest.raises(GatewayHttpError, match="authority changed"):
            invoke()
    else:
        invoke()
    request = client.m_opener.open.call_args.args[0]
    assert request.get_header("If-match") == native_home_etag(selected.home)
    client.m_opener.open.assert_called_once()
