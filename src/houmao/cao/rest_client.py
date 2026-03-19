"""Typed REST client for CAO endpoints."""

from __future__ import annotations

import json
from typing import TypeVar
from urllib import error, parse, request

from pydantic import BaseModel, ValidationError

from .no_proxy import scoped_loopback_no_proxy_for_cao_base_url
from .models import (
    CaoErrorResponse,
    CaoHealthResponse,
    CaoInboxCreateResponse,
    CaoInboxMessage,
    CaoSessionDetail,
    CaoSessionInfo,
    CaoSuccessResponse,
    CaoTerminal,
    CaoTerminalOutputResponse,
)

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class CaoApiError(RuntimeError):
    """Raised when CAO API requests fail.

    Parameters
    ----------
    method:
        HTTP method that failed.
    url:
        Fully-qualified URL.
    detail:
        Structured CAO error detail.
    status_code:
        Optional HTTP status code.
    payload:
        Optional decoded response payload.
    """

    def __init__(
        self,
        *,
        method: str,
        url: str,
        detail: str,
        status_code: int | None = None,
        payload: object | None = None,
    ) -> None:
        self.method = method
        self.url = url
        self.detail = detail
        self.status_code = status_code
        self.payload = payload
        status = f"status={status_code}" if status_code is not None else "status=unavailable"
        super().__init__(f"CAO API error for {method} {url}: {status}, detail={detail}")


class CaoRestClient:
    """HTTP client for CAO session and terminal APIs."""

    def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def health(self) -> CaoHealthResponse:
        """Call `GET /health`."""

        return self._request_model("GET", "/health", CaoHealthResponse)

    def list_sessions(self) -> list[CaoSessionInfo]:
        """Call `GET /sessions`."""

        return self._request_model_list("GET", "/sessions", CaoSessionInfo)

    def create_session(
        self,
        *,
        provider: str,
        agent_profile: str,
        session_name: str | None = None,
        working_directory: str | None = None,
    ) -> CaoTerminal:
        """Call `POST /sessions`."""

        params: dict[str, str] = {
            "provider": provider,
            "agent_profile": agent_profile,
        }
        if session_name:
            params["session_name"] = session_name
        if working_directory:
            params["working_directory"] = working_directory

        return self._request_model(
            "POST",
            "/sessions",
            CaoTerminal,
            params=params,
        )

    def delete_session(self, session_name: str) -> CaoSuccessResponse:
        """Call `DELETE /sessions/{session_name}`."""

        escaped = parse.quote(session_name, safe="")
        return self._request_model("DELETE", f"/sessions/{escaped}", CaoSuccessResponse)

    def get_session_detail(self, session_name: str) -> CaoSessionDetail:
        """Call `GET /sessions/{session_name}`."""

        escaped = parse.quote(session_name, safe="")
        return self._request_model("GET", f"/sessions/{escaped}", CaoSessionDetail)

    def list_session_terminals(self, session_name: str) -> list[CaoTerminal]:
        """Call `GET /sessions/{session_name}/terminals`."""

        escaped = parse.quote(session_name, safe="")
        return self._request_model_list(
            "GET",
            f"/sessions/{escaped}/terminals",
            CaoTerminal,
        )

    def create_terminal(
        self,
        session_name: str,
        *,
        provider: str,
        agent_profile: str,
        working_directory: str | None = None,
    ) -> CaoTerminal:
        """Call `POST /sessions/{session_name}/terminals`."""

        escaped = parse.quote(session_name, safe="")
        params: dict[str, str] = {
            "provider": provider,
            "agent_profile": agent_profile,
        }
        if working_directory:
            params["working_directory"] = working_directory
        return self._request_model(
            "POST",
            f"/sessions/{escaped}/terminals",
            CaoTerminal,
            params=params,
        )

    def get_terminal(self, terminal_id: str) -> CaoTerminal:
        """Call `GET /terminals/{id}`."""

        escaped = parse.quote(terminal_id, safe="")
        return self._request_model("GET", f"/terminals/{escaped}", CaoTerminal)

    def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
        """Call `POST /terminals/{id}/input`."""

        escaped = parse.quote(terminal_id, safe="")
        return self._request_model(
            "POST",
            f"/terminals/{escaped}/input",
            CaoSuccessResponse,
            params={"message": message},
        )

    def get_terminal_output(
        self, terminal_id: str, mode: str = "last"
    ) -> CaoTerminalOutputResponse:
        """Call `GET /terminals/{id}/output`."""

        escaped = parse.quote(terminal_id, safe="")
        return self._request_model(
            "GET",
            f"/terminals/{escaped}/output",
            CaoTerminalOutputResponse,
            params={"mode": mode},
        )

    def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
        """Call `POST /terminals/{id}/exit`."""

        escaped = parse.quote(terminal_id, safe="")
        return self._request_model("POST", f"/terminals/{escaped}/exit", CaoSuccessResponse)

    def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
        """Call `DELETE /terminals/{id}`."""

        escaped = parse.quote(terminal_id, safe="")
        return self._request_model("DELETE", f"/terminals/{escaped}", CaoSuccessResponse)

    def send_inbox_message(
        self,
        receiver_terminal_id: str,
        *,
        sender_id: str,
        message: str,
    ) -> CaoInboxCreateResponse:
        """Call `POST /terminals/{receiver}/inbox/messages`."""

        escaped = parse.quote(receiver_terminal_id, safe="")
        return self._request_model(
            "POST",
            f"/terminals/{escaped}/inbox/messages",
            CaoInboxCreateResponse,
            params={"sender_id": sender_id, "message": message},
        )

    def list_inbox_messages(
        self,
        terminal_id: str,
        *,
        limit: int | None = None,
        status: str | None = None,
    ) -> list[CaoInboxMessage]:
        """Call `GET /terminals/{terminal_id}/inbox/messages`."""

        escaped = parse.quote(terminal_id, safe="")
        params: dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        if status is not None:
            params["status"] = status

        return self._request_model_list(
            "GET",
            f"/terminals/{escaped}/inbox/messages",
            CaoInboxMessage,
            params=params or None,
        )

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

    def _request_model_list(
        self,
        method: str,
        path: str,
        model: type[_ModelT],
        *,
        params: dict[str, str] | None = None,
    ) -> list[_ModelT]:
        payload, status_code, url = self._request_json(method, path, params=params)
        if not isinstance(payload, list):
            raise CaoApiError(
                method=method,
                url=url,
                status_code=status_code,
                detail=f"Expected JSON list response, got {type(payload).__name__}",
                payload=payload,
            )

        items: list[_ModelT] = []
        for index, raw_item in enumerate(payload):
            try:
                items.append(model.model_validate(raw_item))
            except ValidationError as exc:
                raise CaoApiError(
                    method=method,
                    url=url,
                    status_code=status_code,
                    detail=f"$[{index}]: {_format_validation_error(exc)}",
                    payload=raw_item,
                ) from exc
        return items

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> tuple[object, int, str]:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{parse.urlencode(params)}"

        req = request.Request(
            url,
            data=None,
            method=method,
            headers={"Accept": "application/json"},
        )

        try:
            with scoped_loopback_no_proxy_for_cao_base_url(self.base_url):
                with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    status_code = int(resp.status)
                    raw_text = resp.read().decode("utf-8", errors="replace")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            detail, decoded = _extract_error_detail(body)
            raise CaoApiError(
                method=method,
                url=url,
                status_code=int(exc.code),
                detail=detail,
                payload=decoded,
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

        if not raw_text.strip():
            return {}, status_code, url

        try:
            decoded = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise CaoApiError(
                method=method,
                url=url,
                status_code=status_code,
                detail=f"CAO API returned non-JSON response: {raw_text[:200]}",
            ) from exc
        return decoded, status_code, url


def _extract_error_detail(raw_text: str) -> tuple[str, object | None]:
    text = raw_text.strip()
    if not text:
        return "empty error response body", None

    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        return text, text

    if isinstance(decoded, dict):
        try:
            error_payload = CaoErrorResponse.model_validate(decoded)
        except ValidationError:
            detail = decoded.get("detail")
            if isinstance(detail, str):
                return detail, decoded
            if detail is not None:
                return json.dumps(detail, sort_keys=True), decoded
            return json.dumps(decoded, sort_keys=True), decoded

        detail = error_payload.detail
        if isinstance(detail, str):
            return detail, decoded
        return json.dumps(detail, sort_keys=True), decoded

    return json.dumps(decoded, sort_keys=True), decoded


def _format_validation_error(exc: ValidationError) -> str:
    issues: list[str] = []
    for issue in exc.errors(include_url=False):
        location = _format_error_location(issue.get("loc", ()))
        message = str(issue.get("msg", "validation failed"))
        issues.append(f"{location}: {message}")
        if len(issues) >= 3:
            break
    return "; ".join(issues) if issues else "response validation failed"


def _format_error_location(location: object) -> str:
    if not isinstance(location, tuple) or not location:
        return "$"

    path = "$"
    for item in location:
        if isinstance(item, int):
            path += f"[{item}]"
            continue
        path += f".{item}"
    return path
