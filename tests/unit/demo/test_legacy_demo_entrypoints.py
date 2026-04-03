from __future__ import annotations

from collections.abc import Callable

import pytest

from houmao.demo.legacy.gateway_mail_wakeup_demo_pack import driver as gateway_mail_wakeup_driver
from houmao.demo.legacy.mail_ping_pong_gateway_demo_pack import driver as mail_ping_pong_driver
from houmao.demo.legacy.tui_mail_gateway_demo_pack import driver as tui_mail_gateway_driver


@pytest.mark.parametrize(
    ("main_fn", "demo_name"),
    [
        (gateway_mail_wakeup_driver.main, "gateway_mail_wakeup_demo_pack"),
        (tui_mail_gateway_driver.main, "tui_mail_gateway_demo_pack"),
        (mail_ping_pong_driver.main, "mail_ping_pong_gateway_demo_pack"),
    ],
)
def test_legacy_demo_entrypoints_fail_fast(
    main_fn: Callable[[list[str] | None], int],
    demo_name: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main_fn(["auto"]) == 1

    captured = capsys.readouterr()
    assert f"Archived demo `{demo_name}` is not runnable." in captured.err
    assert "deprecated project-local mailbox-skill mirror and skill-path prompting contract" in captured.err
    assert "scripts/demo/single-agent-mail-wakeup/" in captured.err
    assert "scripts/demo/single-agent-gateway-wakeup-headless/" in captured.err
