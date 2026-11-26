"""Root HTTP transport for pair discovery and server clients."""

from __future__ import annotations

import json
from typing import Literal, TypeVar
from urllib import error, parse, request

from pydantic import BaseModel, ValidationError

from houmao.cao.no_proxy import scoped_loopback_no_proxy_for_cao_base_url
from houmao.cao.rest_client import CaoApiError, _format_validation_error

_ModelT = TypeVar("_ModelT", bound=BaseModel)
RootResponseFormat = Literal["json", "text", "json-or-text"]


def decode_root_response(raw: bytes, response_format: RootResponseFormat) -> object:
    """Decode UTF-8 text or JSON according to the endpoint contract."""

    body = raw.decode("utf-8")
    if response_format == "text":
        return body
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        if response_format == "json-or-text":
            return body
        raise


def request_root(
    base_url: str,
    method: str,
    path: str,
    *,
    default_timeout_seconds: float,
    params: dict[str, str] | None = None,
    json_body: object | None = None,
    response_format: RootResponseFormat = "json",
    timeout_seconds: float | None = None,
) -> tuple[object, int, str]:
    """Send an unsigned server request with the established root URL and errors."""

    query = parse.urlencode(params or {})
    url = f"{base_url}{path}"
    if query:
        url = f"{url}?{query}"

    data: bytes | None = None
    headers = {"Accept": "application/json"}
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if method.upper() in {"POST", "PUT", "PATCH"}:
        data = b"" if data is None else data

    outgoing = request.Request(url, data=data, method=method, headers=headers)
    try:
        with scoped_loopback_no_proxy_for_cao_base_url(base_url):
            with request.urlopen(
                outgoing, timeout=timeout_seconds or default_timeout_seconds
            ) as response:
                payload = decode_root_response(response.read(), response_format)
                return payload, int(response.status), url
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"detail": body.strip() or str(exc)}
        detail = (
            str(payload["detail"])
            if isinstance(payload, dict) and "detail" in payload
            else f"Unexpected response payload type: {type(payload).__name__}"
        )
        raise CaoApiError(
            method=method, url=url, detail=detail, status_code=int(exc.code), payload=payload
        ) from exc
    except error.URLError as exc:
        raise CaoApiError(method=method, url=url, detail=str(exc.reason)) from exc
    except (TimeoutError, OSError) as exc:
        raise CaoApiError(
            method=method,
            url=url,
            detail=f"Connection failed after {default_timeout_seconds}s: {exc}",
        ) from exc


def validate_root_model(
    method: str, response: tuple[object, int, str], model: type[_ModelT]
) -> _ModelT:
    """Validate a root response while preserving its HTTP status and error payload."""

    payload, status_code, url = response
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
