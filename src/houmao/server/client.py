"""Client helpers for `houmao-server`."""

from __future__ import annotations

import json
from typing import TypeVar
from urllib import error, parse, request

from pydantic import BaseModel, ValidationError

from houmao.cao.rest_client import CaoApiError, CaoRestClient, _format_validation_error
from houmao.cao.no_proxy import scoped_loopback_no_proxy_for_cao_base_url
from houmao.cao.models import CaoSessionDetail

from .models import (
    HoumaoCurrentInstance,
    HoumaoHealthResponse,
    HoumaoInstallAgentProfileRequest,
    HoumaoInstallAgentProfileResponse,
    HoumaoRegisterLaunchRequest,
    HoumaoRegisterLaunchResponse,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalStateResponse,
    WorkingDirectoryResponse,
)

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class HoumaoServerClient(CaoRestClient):
    """HTTP client for `houmao-server` compatibility and extension routes."""

    def health_extended(self) -> HoumaoHealthResponse:
        """Call `GET /health` and parse Houmao extensions."""

        return self._request_model("GET", "/health", HoumaoHealthResponse)

    def get_session(self, session_name: str) -> CaoSessionDetail:
        """Call `GET /sessions/{session_name}`."""

        return self.get_session_detail(session_name)

    def delete_session(self, session_name: str) -> dict[str, object] | None:
        """Call `DELETE /sessions/{session_name}`."""

        escaped = parse.quote(session_name, safe="")
        payload, _status_code, _url = self._request_json("DELETE", f"/sessions/{escaped}")
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise CaoApiError(
                method="DELETE",
                url=f"{self.base_url}/sessions/{escaped}",
                detail="Expected JSON object response for session deletion",
                payload=payload,
            )
        return payload

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

        return self._request_model(
            "GET",
            "/houmao/server/current-instance",
            HoumaoCurrentInstance,
        )

    def terminal_state(self, terminal_id: str) -> HoumaoTerminalStateResponse:
        """Call `GET /houmao/terminals/{terminal_id}/state`."""

        escaped = parse.quote(terminal_id, safe="")
        return self._request_model(
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
        return self._request_model(
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
        return self._request_model(
            "POST",
            "/houmao/agent-profiles/install",
            HoumaoInstallAgentProfileResponse,
            params={key: str(value) for key, value in query_params.items()},
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> tuple[object, int, str]:
        query = parse.urlencode(params or {})
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"

        data: bytes | None = None
        if method.upper() in {"POST", "PUT", "PATCH"}:
            data = b""

        req = request.Request(url, data=data, method=method, headers={"Accept": "application/json"})
        try:
            with scoped_loopback_no_proxy_for_cao_base_url(self.base_url):
                with request.urlopen(req, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
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

    def _request_model(
        self,
        method: str,
        path: str,
        model: type[_ModelT],
        *,
        params: dict[str, str] | None = None,
    ) -> _ModelT:
        payload, status_code, url = self._request_json(method, path, params=params)
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
