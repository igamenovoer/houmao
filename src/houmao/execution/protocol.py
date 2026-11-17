"""Bounded JSON framing for private finite execution operations."""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from houmao.execution.models import ExecutionRequestV1, ExecutionResponseV1

MAX_REQUEST_BYTES = 1_048_576
MAX_RESPONSE_BYTES = 8_388_608
MAX_JSON_DEPTH = 32
_Model = TypeVar("_Model", bound=BaseModel)


class ExecutionProtocolError(ValueError):
    """Report protocol errors without reproducing credential-bearing input."""


def encode_request(request: ExecutionRequestV1) -> bytes:
    """Encode one size/depth-bounded request as a single JSON document."""

    return _encode(request, limit=MAX_REQUEST_BYTES)


def decode_request(payload: bytes) -> ExecutionRequestV1:
    """Validate a single request while keeping input values out of error diagnostics."""

    return _decode(payload, ExecutionRequestV1, limit=MAX_REQUEST_BYTES)


def encode_response(response: ExecutionResponseV1) -> bytes:
    """Encode one finite owner response, rejecting oversized output."""

    return _encode(response, limit=MAX_RESPONSE_BYTES)


def decode_response(payload: bytes) -> ExecutionResponseV1:
    """Validate a finite response without trusting extra stdout or schema coercions."""

    return _decode(payload, ExecutionResponseV1, limit=MAX_RESPONSE_BYTES)


def _encode(model: BaseModel, *, limit: int) -> bytes:
    """Apply common JSON bounds to outgoing protocol documents."""

    try:
        body = model.model_dump(mode="json")
        _check_depth(body)
        payload = json.dumps(
            body, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode()
        if len(payload) + 1 > limit:
            raise ExecutionProtocolError("Execution document exceeds its size limit")
        return payload + b"\n"
    except (TypeError, ValueError, RecursionError):
        raise ExecutionProtocolError(
            "Execution document could not be encoded within protocol limits"
        ) from None


def _decode(payload: bytes, model: type[_Model], *, limit: int) -> _Model:
    """Bound input before validating its versioned model."""

    if len(payload) > limit:
        raise ExecutionProtocolError("Execution document exceeds its size limit")
    try:
        document: object = json.loads(payload, object_pairs_hook=_unique_object)
        _check_depth(document)
        # JSON mode correctly represents immutable tuples as arrays while retaining scalar strictness.
        return model.model_validate_json(payload)
    except (ValueError, TypeError, RecursionError, UnicodeDecodeError, ValidationError):
        raise ExecutionProtocolError("Execution document is malformed or incompatible") from None


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate keys rather than choosing an ambiguous operation or authority."""

    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate execution-document key")
        result[key] = value
    return result


def _check_depth(value: object, depth: int = 0) -> None:
    """Reject pathological nesting before model parsing or output encoding."""

    if depth > MAX_JSON_DEPTH:
        raise ExecutionProtocolError("Execution document nesting exceeds its limit")
    if isinstance(value, dict):
        for child in value.values():
            _check_depth(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _check_depth(child, depth + 1)
