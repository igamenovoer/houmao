"""Client helpers for `houmao-server`."""

from __future__ import annotations

import json
from typing import TypeVar
from urllib import error, parse, request

from pydantic import BaseModel, ValidationError

from houmao.cao.rest_client import CaoApiError, CaoRestClient, _format_validation_error
from houmao.cao.no_proxy import scoped_loopback_no_proxy_for_cao_base_url
from houmao.cao.models import CaoSessionDetail, CaoSuccessResponse

from .models import (
    HoumaoCurrentInstance,
    HoumaoHeadlessLaunchRequest,
    HoumaoHeadlessLaunchResponse,
    HoumaoHeadlessTurnAcceptedResponse,
    HoumaoHeadlessTurnEventsResponse,
    HoumaoHeadlessTurnRequest,
    HoumaoHeadlessTurnStatusResponse,
    HoumaoHealthResponse,
    HoumaoInstallAgentProfileRequest,
    HoumaoInstallAgentProfileResponse,
    HoumaoManagedAgentActionResponse,
    HoumaoManagedAgentHistoryResponse,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentListResponse,
    HoumaoManagedAgentStateResponse,
    HoumaoRegisterLaunchRequest,
    HoumaoRegisterLaunchResponse,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalStateResponse,
    WorkingDirectoryResponse,
)

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class HoumaoServerClient(CaoRestClient):
    """HTTP client for `houmao-server` compatibility and extension routes."""

    def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
        """Initialize the pair-owned server client."""

        super().__init__(base_url, timeout_seconds=timeout_seconds, path_prefix="/cao")

    def health_extended(self) -> HoumaoHealthResponse:
        """Call `GET /health` and parse Houmao extensions."""

        return self._request_root_model("GET", "/health", HoumaoHealthResponse)

    def get_session(self, session_name: str) -> CaoSessionDetail:
        """Call `GET /sessions/{session_name}`."""

        return self.get_session_detail(session_name)

    def delete_session(self, session_name: str) -> CaoSuccessResponse:
        """Call `DELETE /sessions/{session_name}`."""

        escaped = parse.quote(session_name, safe="")
        return self._request_model("DELETE", f"/sessions/{escaped}", CaoSuccessResponse)

    def get_terminal_working_directory(self, terminal_id: str) -> WorkingDirectoryResponse:
        """Call `GET /terminals/{terminal_id}/working-directory`."""

        escaped = parse.quote(terminal_id, safe="")
        return self._request_model(
            "GET",
            f"/terminals/{escaped}/working-directory",
            WorkingDirectoryResponse,
        )

    def current_instance(self) -> HoumaoCurrentInstance:
        """Call `GET /houmao/server/current-instance`."""

        return self._request_root_model(
            "GET",
            "/houmao/server/current-instance",
            HoumaoCurrentInstance,
        )

    def terminal_state(self, terminal_id: str) -> HoumaoTerminalStateResponse:
        """Call `GET /houmao/terminals/{terminal_id}/state`."""

        escaped = parse.quote(terminal_id, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/terminals/{escaped}/state",
            HoumaoTerminalStateResponse,
        )

    def terminal_history(
        self,
        terminal_id: str,
        *,
        limit: int | None = None,
    ) -> HoumaoTerminalHistoryResponse:
        """Call `GET /houmao/terminals/{terminal_id}/history`."""

        escaped = parse.quote(terminal_id, safe="")
        params: dict[str, str] | None = None
        if limit is not None:
            params = {"limit": str(limit)}
        return self._request_root_model(
            "GET",
            f"/houmao/terminals/{escaped}/history",
            HoumaoTerminalHistoryResponse,
            params=params,
        )

    def register_launch(
        self, request_model: HoumaoRegisterLaunchRequest
    ) -> HoumaoRegisterLaunchResponse:
        """Call `POST /houmao/launches/register`."""

        query_params = {
            key: value
            for key, value in request_model.model_dump(mode="json").items()
            if value is not None
        }
        return self._request_model(
            "POST",
            "/houmao/launches/register",
            HoumaoRegisterLaunchResponse,
            params={key: str(value) for key, value in query_params.items()},
        )

    def install_agent_profile(
        self, request_model: HoumaoInstallAgentProfileRequest
    ) -> HoumaoInstallAgentProfileResponse:
        """Call `POST /houmao/agent-profiles/install`."""

        query_params = {
            key: value
            for key, value in request_model.model_dump(mode="json").items()
            if value is not None
        }
        return self._request_root_model(
            "POST",
            "/houmao/agent-profiles/install",
            HoumaoInstallAgentProfileResponse,
            params={key: str(value) for key, value in query_params.items()},
        )

    def list_managed_agents(self) -> HoumaoManagedAgentListResponse:
        """Call `GET /houmao/agents`."""

        return self._request_root_model("GET", "/houmao/agents", HoumaoManagedAgentListResponse)

    def get_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentIdentity:
        """Call `GET /houmao/agents/{agent_ref}`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}",
            HoumaoManagedAgentIdentity,
        )

    def get_managed_agent_state(self, agent_ref: str) -> HoumaoManagedAgentStateResponse:
        """Call `GET /houmao/agents/{agent_ref}/state`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/state",
            HoumaoManagedAgentStateResponse,
        )

    def get_managed_agent_history(
        self,
        agent_ref: str,
        *,
        limit: int | None = None,
    ) -> HoumaoManagedAgentHistoryResponse:
        """Call `GET /houmao/agents/{agent_ref}/history`."""

        escaped = parse.quote(agent_ref, safe="")
        params: dict[str, str] | None = None
        if limit is not None:
            params = {"limit": str(limit)}
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped}/history",
            HoumaoManagedAgentHistoryResponse,
            params=params,
        )

    def launch_headless_agent(
        self,
        request_model: HoumaoHeadlessLaunchRequest,
    ) -> HoumaoHeadlessLaunchResponse:
        """Call `POST /houmao/agents/headless/launches`."""

        return self._request_root_model(
            "POST",
            "/houmao/agents/headless/launches",
            HoumaoHeadlessLaunchResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def stop_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentActionResponse:
        """Call `POST /houmao/agents/{agent_ref}/stop`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/stop",
            HoumaoManagedAgentActionResponse,
        )

    def submit_headless_turn(
        self,
        agent_ref: str,
        request_model: HoumaoHeadlessTurnRequest,
    ) -> HoumaoHeadlessTurnAcceptedResponse:
        """Call `POST /houmao/agents/{agent_ref}/turns`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/turns",
            HoumaoHeadlessTurnAcceptedResponse,
            json_body=request_model.model_dump(mode="json"),
        )

    def get_headless_turn_status(
        self,
        agent_ref: str,
        turn_id: str,
    ) -> HoumaoHeadlessTurnStatusResponse:
        """Call `GET /houmao/agents/{agent_ref}/turns/{turn_id}`."""

        escaped_agent = parse.quote(agent_ref, safe="")
        escaped_turn = parse.quote(turn_id, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped_agent}/turns/{escaped_turn}",
            HoumaoHeadlessTurnStatusResponse,
        )

    def get_headless_turn_events(
        self,
        agent_ref: str,
        turn_id: str,
    ) -> HoumaoHeadlessTurnEventsResponse:
        """Call `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events`."""

        escaped_agent = parse.quote(agent_ref, safe="")
        escaped_turn = parse.quote(turn_id, safe="")
        return self._request_root_model(
            "GET",
            f"/houmao/agents/{escaped_agent}/turns/{escaped_turn}/events",
            HoumaoHeadlessTurnEventsResponse,
        )

    def get_headless_turn_artifact_text(
        self,
        agent_ref: str,
        turn_id: str,
        *,
        artifact_name: str,
    ) -> str:
        """Call one raw headless artifact route and return the text body."""

        escaped_agent = parse.quote(agent_ref, safe="")
        escaped_turn = parse.quote(turn_id, safe="")
        payload, _status_code, _url = self._request_root_json(
            "GET",
            f"/houmao/agents/{escaped_agent}/turns/{escaped_turn}/artifacts/{artifact_name}",
            raw_text_ok=True,
        )
        if isinstance(payload, str):
            return payload
        return json.dumps(payload)

    def interrupt_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentActionResponse:
        """Call `POST /houmao/agents/{agent_ref}/interrupt`."""

        escaped = parse.quote(agent_ref, safe="")
        return self._request_root_model(
            "POST",
            f"/houmao/agents/{escaped}/interrupt",
            HoumaoManagedAgentActionResponse,
        )

    def _request_root_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: object | None = None,
        raw_text_ok: bool = False,
    ) -> tuple[object, int, str]:
        query = parse.urlencode(params or {})
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"

        data: bytes | None = None
        headers = {"Accept": "application/json"}
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if method.upper() in {"POST", "PUT", "PATCH"}:
            data = b"" if data is None else data

        req = request.Request(url, data=data, method=method, headers=headers)
        try:
            with scoped_loopback_no_proxy_for_cao_base_url(self.base_url):
                with request.urlopen(req, timeout=self.timeout_seconds) as response:
                    body_text = response.read().decode("utf-8")
                    try:
                        payload = json.loads(body_text)
                    except json.JSONDecodeError:
                        if raw_text_ok:
                            payload = body_text
                        else:
                            raise
                    return payload, int(response.status), url
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            payload = None
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = {"detail": body.strip() or str(exc)}
            detail = _extract_detail(payload)
            raise CaoApiError(
                method=method,
                url=url,
                detail=detail,
                status_code=int(exc.code),
                payload=payload,
            ) from exc
        except error.URLError as exc:
            raise CaoApiError(
                method=method,
                url=url,
                detail=str(exc.reason),
            ) from exc
        except (TimeoutError, OSError) as exc:
            raise CaoApiError(
                method=method,
                url=url,
                detail=f"Connection failed after {self.timeout_seconds}s: {exc}",
            ) from exc

    def _request_root_model(
        self,
        method: str,
        path: str,
        model: type[_ModelT],
        *,
        params: dict[str, str] | None = None,
        json_body: object | None = None,
    ) -> _ModelT:
        payload, status_code, url = self._request_root_json(
            method,
            path,
            params=params,
            json_body=json_body,
        )
        try:
            return model.model_validate(payload)
        except ValidationError as exc:
            raise CaoApiError(
                method=method,
                url=url,
                status_code=status_code,
                detail=_format_validation_error(exc),
                payload=payload,
            ) from exc


def _extract_detail(payload: object) -> str:
    if isinstance(payload, dict) and "detail" in payload:
        return str(payload["detail"])
    return f"Unexpected response payload type: {type(payload).__name__}"
