"""HTTP client for live agent gateway surfaces."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TypeVar
from urllib import error, request

from pydantic import BaseModel, ValidationError

from gig_agents.agents.brain_launch_runtime.errors import GatewayHttpError
from gig_agents.agents.brain_launch_runtime.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayHealthResponseV1,
    GatewayHost,
    GatewayRequestCreateV1,
    GatewayStatusV1,
)

_ModelT = TypeVar("_ModelT", bound=BaseModel)


@dataclass(frozen=True)
class GatewayEndpoint:
    """Resolved live gateway listener endpoint."""

    host: GatewayHost
    port: int


class GatewayClient:
    """HTTP client for a live per-agent gateway instance."""

    def __init__(self, *, endpoint: GatewayEndpoint, timeout_seconds: float = 5.0) -> None:
        self.m_endpoint = endpoint
        self.m_timeout_seconds = timeout_seconds

    def health(self) -> GatewayHealthResponseV1:
        """Call `GET /health`."""

        return self._request_model("GET", "/health", GatewayHealthResponseV1)

    def status(self) -> GatewayStatusV1:
        """Call `GET /v1/status`."""

        return self._request_model("GET", "/v1/status", GatewayStatusV1)

    def create_request(self, payload: GatewayRequestCreateV1) -> GatewayAcceptedRequestV1:
        """Call `POST /v1/requests`."""

        return self._request_model(
            "POST",
            "/v1/requests",
            GatewayAcceptedRequestV1,
            body=payload.model_dump(mode="json"),
        )

    def _request_model(
        self,
        method: str,
        path: str,
        model: type[_ModelT],
        *,
        body: dict[str, object] | None = None,
    ) -> _ModelT:
        url = self._build_url(path)
        payload: bytes | None = None
        headers: dict[str, str] = {}
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request_obj = request.Request(
            url=url,
            data=payload,
            method=method,
            headers=headers,
        )
        try:
            with request.urlopen(request_obj, timeout=self.m_timeout_seconds) as response:
                decoded = self._decode_response(
                    method=method,
                    url=url,
                    response=response.read(),
                )
        except error.HTTPError as exc:
            detail = self._decode_error_body(exc.read())
            raise GatewayHttpError(
                method=method,
                url=url,
                detail=detail,
                status_code=exc.code,
            ) from exc
        except error.URLError as exc:
            raise GatewayHttpError(
                method=method,
                url=url,
                detail=str(exc.reason),
            ) from exc

        try:
            return model.model_validate(decoded)
        except ValidationError as exc:
            raise GatewayHttpError(
                method=method,
                url=url,
                detail=f"gateway returned invalid payload: {exc}",
            ) from exc

    def _build_url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.m_endpoint.port}{path}"

    def _decode_response(
        self,
        *,
        method: str,
        url: str,
        response: bytes,
    ) -> object:
        try:
            return json.loads(response.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise GatewayHttpError(
                method=method,
                url=url,
                detail=f"gateway returned invalid JSON: {exc}",
            ) from exc

    def _decode_error_body(self, payload: bytes) -> str:
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return payload.decode("utf-8", errors="replace")
        if isinstance(decoded, dict) and "detail" in decoded:
            detail = decoded["detail"]
            if isinstance(detail, str):
                return detail
            return json.dumps(detail, sort_keys=True)
        return json.dumps(decoded, sort_keys=True)
