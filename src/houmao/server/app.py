"""FastAPI application factory for `houmao-server`."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib import parse

from fastapi import FastAPI, Query, Response

from .config import HoumaoServerConfig
from .models import (
    HoumaoCurrentInstance,
    HoumaoHealthResponse,
    HoumaoRegisterLaunchRequest,
    HoumaoRegisterLaunchResponse,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalStateResponse,
    TerminalId,
)
from .service import HoumaoServerService


def create_app(
    *,
    config: HoumaoServerConfig | None = None,
    service: HoumaoServerService | None = None,
) -> FastAPI:
    """Create a configured `houmao-server` FastAPI application."""

    resolved_config = config or HoumaoServerConfig()
    resolved_service = service or HoumaoServerService(config=resolved_config)

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved_service.startup()
        app.state.houmao_service = resolved_service
        try:
            yield
        finally:
            resolved_service.shutdown()

    app = FastAPI(
        title="houmao-server",
        description="Houmao-owned CAO-compatible HTTP service",
        version="0.1.0",
        lifespan=_lifespan,
    )

    @app.get("/health")
    def health() -> HoumaoHealthResponse:
        return resolved_service.health_response()

    @app.get("/houmao/server/current-instance")
    def current_instance() -> HoumaoCurrentInstance:
        return resolved_service.current_instance_response()

    @app.post("/sessions", status_code=201)
    def create_session(
        provider: str,
        agent_profile: str,
        session_name: str | None = None,
        working_directory: str | None = None,
    ) -> Response:
        result = resolved_service.proxy(
            method="POST",
            path="/sessions",
            params=_drop_none(
                {
                    "provider": provider,
                    "agent_profile": agent_profile,
                    "session_name": session_name,
                    "working_directory": working_directory,
                }
            ),
        )
        if 200 <= result.status_code < 300:
            resolved_service.sync_created_terminal(result.json_payload)
        return result.to_fastapi_response()

    @app.get("/sessions")
    def list_sessions() -> Response:
        return resolved_service.proxy(method="GET", path="/sessions").to_fastapi_response()

    @app.get("/sessions/{session_name}")
    def get_session(session_name: str) -> Response:
        return resolved_service.proxy(
            method="GET",
            path=f"/sessions/{_quote_path_segment(session_name)}",
        ).to_fastapi_response()

    @app.delete("/sessions/{session_name}")
    def delete_session(session_name: str) -> Response:
        result = resolved_service.proxy(
            method="DELETE",
            path=f"/sessions/{_quote_path_segment(session_name)}",
        )
        if 200 <= result.status_code < 300:
            resolved_service.handle_deleted_session(session_name)
        return result.to_fastapi_response()

    @app.post("/sessions/{session_name}/terminals", status_code=201)
    def create_terminal(
        session_name: str,
        provider: str,
        agent_profile: str,
        working_directory: str | None = None,
    ) -> Response:
        result = resolved_service.proxy(
            method="POST",
            path=f"/sessions/{_quote_path_segment(session_name)}/terminals",
            params=_drop_none(
                {
                    "provider": provider,
                    "agent_profile": agent_profile,
                    "working_directory": working_directory,
                }
            ),
        )
        if 200 <= result.status_code < 300:
            resolved_service.sync_created_terminal(result.json_payload)
        return result.to_fastapi_response()

    @app.get("/sessions/{session_name}/terminals")
    def list_session_terminals(session_name: str) -> Response:
        return resolved_service.proxy(
            method="GET",
            path=f"/sessions/{_quote_path_segment(session_name)}/terminals",
        ).to_fastapi_response()

    @app.get("/terminals/{terminal_id}")
    def get_terminal(terminal_id: TerminalId) -> Response:
        return resolved_service.proxy(
            method="GET",
            path=f"/terminals/{_quote_path_segment(terminal_id)}",
        ).to_fastapi_response()

    @app.get("/terminals/{terminal_id}/working-directory")
    def get_terminal_working_directory(terminal_id: TerminalId) -> Response:
        return resolved_service.proxy(
            method="GET",
            path=f"/terminals/{_quote_path_segment(terminal_id)}/working-directory",
        ).to_fastapi_response()

    @app.post("/terminals/{terminal_id}/input")
    def send_input(terminal_id: TerminalId, message: str) -> Response:
        result = resolved_service.proxy(
            method="POST",
            path=f"/terminals/{_quote_path_segment(terminal_id)}/input",
            params={"message": message},
        )
        if 200 <= result.status_code < 300:
            resolved_service.note_prompt_submission(terminal_id=terminal_id, message=message)
        return result.to_fastapi_response()

    @app.get("/terminals/{terminal_id}/output")
    def get_output(terminal_id: TerminalId, mode: str = "full") -> Response:
        return resolved_service.proxy(
            method="GET",
            path=f"/terminals/{_quote_path_segment(terminal_id)}/output",
            params={"mode": mode},
        ).to_fastapi_response()

    @app.post("/terminals/{terminal_id}/exit")
    def exit_terminal(terminal_id: TerminalId) -> Response:
        return resolved_service.proxy(
            method="POST",
            path=f"/terminals/{_quote_path_segment(terminal_id)}/exit",
        ).to_fastapi_response()

    @app.delete("/terminals/{terminal_id}")
    def delete_terminal(terminal_id: TerminalId) -> Response:
        result = resolved_service.proxy(
            method="DELETE",
            path=f"/terminals/{_quote_path_segment(terminal_id)}",
        )
        if 200 <= result.status_code < 300:
            resolved_service.handle_deleted_terminal(terminal_id)
        return result.to_fastapi_response()

    @app.post("/terminals/{receiver_id}/inbox/messages")
    def create_inbox_message(receiver_id: TerminalId, sender_id: str, message: str) -> Response:
        return resolved_service.proxy(
            method="POST",
            path=f"/terminals/{_quote_path_segment(receiver_id)}/inbox/messages",
            params={"sender_id": sender_id, "message": message},
        ).to_fastapi_response()

    @app.get("/terminals/{terminal_id}/inbox/messages")
    def list_inbox_messages(
        terminal_id: TerminalId,
        limit: int = Query(default=10, le=100),
        status: str | None = Query(default=None),
    ) -> Response:
        return resolved_service.proxy(
            method="GET",
            path=f"/terminals/{_quote_path_segment(terminal_id)}/inbox/messages",
            params=_drop_none({"limit": str(limit), "status": status}),
        ).to_fastapi_response()

    @app.post("/houmao/launches/register")
    def register_launch(
        session_name: str,
        tool: str,
        terminal_id: str | None = None,
        manifest_path: str | None = None,
        session_root: str | None = None,
        agent_name: str | None = None,
        agent_id: str | None = None,
        tmux_session_name: str | None = None,
        tmux_window_name: str | None = None,
    ) -> HoumaoRegisterLaunchResponse:
        request_model = HoumaoRegisterLaunchRequest(
            session_name=session_name,
            terminal_id=terminal_id,
            tool=tool,
            manifest_path=manifest_path,
            session_root=session_root,
            agent_name=agent_name,
            agent_id=agent_id,
            tmux_session_name=tmux_session_name,
            tmux_window_name=tmux_window_name,
        )
        return resolved_service.register_launch(request_model)

    @app.get("/houmao/terminals/{terminal_id}/state")
    def terminal_state(terminal_id: TerminalId) -> HoumaoTerminalStateResponse:
        return resolved_service.terminal_state(terminal_id)

    @app.get("/houmao/terminals/{terminal_id}/history")
    def terminal_history(
        terminal_id: TerminalId,
        limit: int = Query(default=100, ge=1, le=500),
    ) -> HoumaoTerminalHistoryResponse:
        return resolved_service.terminal_history(terminal_id, limit=limit)

    return app


def _drop_none(values: dict[str, str | None]) -> dict[str, str]:
    return {key: value for key, value in values.items() if value is not None}


def _quote_path_segment(value: str) -> str:
    """Percent-encode one child-CAO path segment."""

    return parse.quote(value, safe="")
