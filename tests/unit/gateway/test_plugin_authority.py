"""Public notification events reject delivery and owner authority overrides."""

from __future__ import annotations

from pydantic import ValidationError
import pytest

from houmao.gateway.plugins import PluginEvent


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("kind", "interrupt"),
        ("sequence", "<[Enter]>"),
        ("raw_input", "<[Enter]>"),
        ("admission_policy", "always"),
        ("execution", {"model": {"name": "override"}}),
        ("credential_ref", {"file": "/private/other.json"}),
        ("owner", {"agent_id": "other-owner"}),
        ("sender", {"account": "other-account"}),
        ("binding_id", "other-binding"),
    ],
)
def test_event_cannot_request_privileged_delivery(field: str, value: object) -> None:
    """Ordinary notifications cannot select raw input, authority, or admission bypasses."""

    with pytest.raises(ValidationError):
        PluginEvent.model_validate({"source_event_id": "one", "text": "ordinary", field: value})
