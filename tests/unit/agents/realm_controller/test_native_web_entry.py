"""Protect the exact loopback authority and native credential representation."""

from urllib.parse import parse_qs, urlsplit

import pytest

from houmao.agents.realm_controller.backends.web_entry import NativeWebEntry


def test_native_entry_encodes_each_component_and_hides_credentials() -> None:
    """Use the verified origin and preserve the provider's literal component values."""

    origin = "http://[::1]:1234"
    entry = NativeWebEntry(
        origin=origin,
        path="/sessions/example id?&=+#雪",
        query=(("query &name", "query&secret= +#?"),),
        fragment=(("fragment/+", "private-fragment=?&+"),),
    )
    result = urlsplit(entry.redirect_url(expected_origin=origin + "/"))
    assert result.scheme == "http" and result.netloc == "[::1]:1234"
    assert result.path == "/sessions/example%20id%3F%26%3D%2B%23%E9%9B%AA"
    assert parse_qs(result.query) == {"query &name": ["query&secret= +#?"]}
    assert parse_qs(result.fragment) == {"fragment/+": ["private-fragment=?&+"]}
    assert "private-fragment" not in repr(entry) and "query&secret" not in repr(entry)


@pytest.mark.parametrize(
    "origin,path",
    [
        ("http://127.0.0.1:1235", "/"),
        ("http://localhost:1234", "/"),
        ("https://127.0.0.1:1234", "/"),
        ("http://user:private@127.0.0.1:1234", "/"),
        ("http://127.0.0.1:1234?private", "/"),
        ("http://127.0.0.1:1234#", "/"),
        ("\x00http://127.0.0.1:1234", "/"),
        ("http://127.0.0.1:1234", "//private.example"),
        ("http://127.0.0.1:1234", "/\\private.example"),
        ("http://127.0.0.1:1234", "https://private.example"),
        ("http://127.0.0.1:1234", "/sessions/../private"),
    ],
)
def test_native_entry_rejects_invalid_location_with_fixed_error(origin: str, path: str) -> None:
    """Refuse invalid components without echoing native origin, path, or secrets."""

    entry = NativeWebEntry(origin=origin, path=path, query=(("token", "private"),))
    with pytest.raises(ValueError, match="^Native Web browser location is invalid$"):
        entry.redirect_url(expected_origin="http://127.0.0.1:1234")
