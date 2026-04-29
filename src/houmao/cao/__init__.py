"""Shared CAO REST integration modules."""

from .no_proxy import (
    SUPPORTED_LOOPBACK_CAO_BASE_URLS,
    describe_supported_loopback_cao_base_urls,
    extract_cao_base_url_host_port,
    inject_loopback_no_proxy_env,
    inject_loopback_no_proxy_env_for_cao_base_url,
    is_supported_loopback_cao_base_url,
    normalize_cao_base_url,
    scoped_loopback_no_proxy_for_cao_base_url,
)
from .models import (
    CaoHealthResponse,
    CaoInboxCreateResponse,
    CaoInboxMessage,
    CaoInboxMessageStatus,
    CaoSessionInfo,
    CaoSuccessResponse,
    CaoTerminal,
    CaoTerminalOutputResponse,
    CaoTerminalStatus,
)
from .rest_client import CaoApiError, CaoRestClient

__all__ = [
    "CaoApiError",
    "CaoHealthResponse",
    "CaoInboxCreateResponse",
    "CaoInboxMessage",
    "CaoInboxMessageStatus",
    "CaoRestClient",
    "CaoSessionInfo",
    "CaoSuccessResponse",
    "CaoTerminal",
    "CaoTerminalOutputResponse",
    "CaoTerminalStatus",
    "SUPPORTED_LOOPBACK_CAO_BASE_URLS",
    "describe_supported_loopback_cao_base_urls",
    "extract_cao_base_url_host_port",
    "inject_loopback_no_proxy_env",
    "inject_loopback_no_proxy_env_for_cao_base_url",
    "is_supported_loopback_cao_base_url",
    "normalize_cao_base_url",
    "scoped_loopback_no_proxy_for_cao_base_url",
]
