"""Loopback no-proxy helpers shared by launcher and runtime paths."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Mapping, MutableMapping
from urllib import parse

_SUPPORTED_LOOPBACK_CAO_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1"})
SUPPORTED_LOOPBACK_CAO_BASE_URLS: tuple[str, ...] = (
    "http://localhost:<port>",
    "http://127.0.0.1:<port>",
)
LOOPBACK_NO_PROXY_ENTRIES: tuple[str, ...] = ("localhost", "127.0.0.1", "::1")
PRESERVE_NO_PROXY_ENV_VAR = "HOUMAO_PRESERVE_NO_PROXY_ENV"


def normalize_cao_base_url(base_url: str) -> str:
    """Normalize a CAO base URL to `http://<host>:<port>`.

    Parameters
    ----------
    base_url:
        Candidate CAO base URL.

    Returns
    -------
    str
        Normalized URL (`http://<host>:<port>`).

    Raises
    ------
    ValueError
        If the URL is empty, malformed, or not `http://<host>:<port>`.
    """

    text = base_url.strip().rstrip("/")
    if not text:
        raise ValueError("must not be empty")

    parsed = parse.urlsplit(text)
    if parsed.scheme != "http":
        raise ValueError("must use `http` scheme")
    if parsed.hostname is None or parsed.port is None:
        raise ValueError("must include host and port")
    if parsed.path not in ("", "/"):
        raise ValueError("must not include a path component")
    if parsed.query or parsed.fragment:
        raise ValueError("must not include query or fragment components")

    return f"http://{parsed.hostname}:{parsed.port}"


def extract_cao_base_url_host_port(base_url: str) -> tuple[str, int]:
    """Return normalized CAO base URL host and port.

    Parameters
    ----------
    base_url:
        Candidate CAO base URL.

    Returns
    -------
    tuple[str, int]
        Normalized host and explicit port.
    """

    normalized = normalize_cao_base_url(base_url)
    parsed = parse.urlsplit(normalized)
    host = parsed.hostname
    port = parsed.port
    if host is None or port is None:
        raise ValueError("must include host and port")
    return host, port


def describe_supported_loopback_cao_base_urls() -> str:
    """Return a human-readable description of supported loopback CAO URLs."""

    return ", ".join(SUPPORTED_LOOPBACK_CAO_BASE_URLS)


def is_supported_loopback_cao_base_url(base_url: str) -> bool:
    """Return whether a URL is one of the supported loopback CAO base URLs.

    Parameters
    ----------
    base_url:
        Candidate CAO base URL.

    Returns
    -------
    bool
        `True` when the URL is a supported loopback value.
    """

    try:
        host, port = extract_cao_base_url_host_port(base_url)
    except ValueError:
        return False
    return host in _SUPPORTED_LOOPBACK_CAO_HOSTS and port > 0


def merge_loopback_no_proxy(
    primary: str | None,
    secondary: str | None,
) -> str:
    """Merge `NO_PROXY`/`no_proxy` values and ensure loopback coverage.

    Parameters
    ----------
    primary:
        Existing `NO_PROXY` value.
    secondary:
        Existing `no_proxy` value.

    Returns
    -------
    str
        Comma-separated merged value with dedupe and loopback entries appended.
    """

    entries: list[str] = []
    seen: set[str] = set()

    for raw in (primary, secondary):
        for token in _split_no_proxy(raw):
            key = token.lower()
            if key in seen:
                continue
            seen.add(key)
            entries.append(token)

    for token in LOOPBACK_NO_PROXY_ENTRIES:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        entries.append(token)

    return ",".join(entries)


def should_preserve_no_proxy_env(env: Mapping[str, str]) -> bool:
    """Return whether preserve mode is enabled.

    Parameters
    ----------
    env:
        Environment mapping to inspect.

    Returns
    -------
    bool
        `True` when `HOUMAO_PRESERVE_NO_PROXY_ENV=1`.
    """

    return env.get(PRESERVE_NO_PROXY_ENV_VAR) == "1"


def inject_loopback_no_proxy_env(env: MutableMapping[str, str]) -> bool:
    """Inject loopback entries into `NO_PROXY`/`no_proxy` unless preserve mode.

    Parameters
    ----------
    env:
        Environment mapping to mutate.

    Returns
    -------
    bool
        `True` when mutation was applied, `False` when preserve mode skipped it.
    """

    if should_preserve_no_proxy_env(env):
        return False

    merged = merge_loopback_no_proxy(
        env.get("NO_PROXY"),
        env.get("no_proxy"),
    )
    env["NO_PROXY"] = merged
    env["no_proxy"] = merged
    return True


def inject_loopback_no_proxy_env_for_cao_base_url(
    env: MutableMapping[str, str],
    *,
    base_url: str,
) -> bool:
    """Inject loopback no-proxy entries for supported loopback CAO base URLs.

    Parameters
    ----------
    env:
        Environment mapping to mutate.
    base_url:
        CAO API base URL used for the request/session.

    Returns
    -------
    bool
        `True` when loopback injection was applied.
    """

    if not is_supported_loopback_cao_base_url(base_url):
        return False
    return inject_loopback_no_proxy_env(env)


@contextmanager
def scoped_loopback_no_proxy_for_cao_base_url(base_url: str) -> Iterator[bool]:
    """Temporarily inject loopback no-proxy values into process env.

    Parameters
    ----------
    base_url:
        CAO API base URL associated with the HTTP request.

    Yields
    ------
    bool
        Whether loopback injection was applied.
    """

    had_upper = "NO_PROXY" in os.environ
    had_lower = "no_proxy" in os.environ
    previous_upper = os.environ.get("NO_PROXY")
    previous_lower = os.environ.get("no_proxy")

    applied = inject_loopback_no_proxy_env_for_cao_base_url(
        os.environ,
        base_url=base_url,
    )
    try:
        yield applied
    finally:
        if applied:
            if had_upper and previous_upper is not None:
                os.environ["NO_PROXY"] = previous_upper
            else:
                os.environ.pop("NO_PROXY", None)
            if had_lower and previous_lower is not None:
                os.environ["no_proxy"] = previous_lower
            else:
                os.environ.pop("no_proxy", None)


def _split_no_proxy(raw: str | None) -> list[str]:
    if raw is None:
        return []
    tokens = [item.strip() for item in raw.split(",")]
    return [item for item in tokens if item]
