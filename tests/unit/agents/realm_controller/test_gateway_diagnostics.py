from __future__ import annotations

import json
from pathlib import Path

from houmao.agents.realm_controller.gateway_diagnostics import GatewayDiagnosticLogger
from houmao.agents.realm_controller.gateway_models import GatewayDiagnosticLoggingConfigV1


def _entries(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def test_gateway_diagnostic_logger_is_disabled_by_default(tmp_path: Path) -> None:
    log_path = tmp_path / "diagnostics" / "gateway-diagnostic.log"
    logger = GatewayDiagnosticLogger(
        config=GatewayDiagnosticLoggingConfigV1(),
        log_path=log_path,
    )

    logger.emit(level="info", event="gateway.test", fields={"path": "/health"})

    assert not log_path.exists()


def test_gateway_diagnostic_logger_writes_safe_enabled_entries(tmp_path: Path) -> None:
    log_path = tmp_path / "diagnostics" / "gateway-diagnostic.log"
    logger = GatewayDiagnosticLogger(
        config=GatewayDiagnosticLoggingConfigV1(enabled=True),
        log_path=log_path,
    )

    logger.emit(
        level="info",
        event="gateway.test",
        fields={
            "path": "/v1/mail/send",
            "body_content": "do not write me",
            "authorization": "Bearer nope",
            "attachment_count": 1,
        },
    )

    entries = _entries(log_path)
    assert entries == [
        {
            "attachment_count": 1,
            "event": "gateway.test",
            "level": "info",
            "path": "/v1/mail/send",
            "schema_version": 1,
            "timestamp_utc": entries[0]["timestamp_utc"],
        }
    ]
    log_text = log_path.read_text(encoding="utf-8")
    assert "do not write me" not in log_text
    assert "Bearer nope" not in log_text


def test_gateway_diagnostic_logger_deduplicates_consecutive_warning_entries(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "diagnostics" / "gateway-diagnostic.log"
    logger = GatewayDiagnosticLogger(
        config=GatewayDiagnosticLoggingConfigV1(enabled=True),
        log_path=log_path,
    )

    for _ in range(3):
        logger.emit(
            level="warning",
            event="gateway.http_validation_failed",
            fields={"path": "/v1/mail/send", "status_code": 422, "request_id": "volatile"},
        )
    logger.emit(level="info", event="gateway.test_after_warning")

    entries = _entries(log_path)
    assert [entry["event"] for entry in entries] == [
        "gateway.http_validation_failed",
        "diagnostic.dedup_summary",
        "gateway.test_after_warning",
    ]
    assert entries[1]["suppressed_count"] == 2
    assert entries[1]["first_event"] == "gateway.http_validation_failed"


def test_gateway_diagnostic_logger_rotates_bounded_files(tmp_path: Path) -> None:
    log_path = tmp_path / "diagnostics" / "gateway-diagnostic.log"
    logger = GatewayDiagnosticLogger(
        config=GatewayDiagnosticLoggingConfigV1(
            enabled=True,
            max_bytes=500,
            backup_count=2,
        ),
        log_path=log_path,
    )

    for index in range(12):
        logger.emit(
            level="info",
            event="gateway.rotation_test",
            fields={"path": "/health", "index": index, "padding": "x" * 40},
        )

    assert log_path.exists()
    assert log_path.with_name("gateway-diagnostic.log.1").exists()
    assert log_path.with_name("gateway-diagnostic.log.2").exists()
    assert not log_path.with_name("gateway-diagnostic.log.3").exists()
    assert log_path.stat().st_size <= 500
